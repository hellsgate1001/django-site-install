import sys
import os
import shutil
import subprocess
import scriptutil
import re
import time
import getpass
from optparse import OptionParser

"""
Command line options for this script
-c, --python-command: The specific command to use wen calling python scripts
    Defaults to 'python'. OPTIONAL
-p, --project-name: Name of the project you wish to create.  Will
    also be used as the name of the gitrepo. REQUIRED
-d, --directory: The base directory to install the project to .  Defaults to
    /var/projects, so project will be instaled to /var/projects/<project-name>
    OPTIONAL
-g, --git-repo: Base directory for the git repo.  Defaults to /var/git-master-repos,
    so repo will be created at /var/git-master-repos/<project-name>. OPTIONAL
"""

basefile = 'basesite.tar.gz'

# Default Values
defaultdirectory = '/var/projects'
defaultrepo = '/var/git-master-repos'

# Command line options
parser = OptionParser()
parser.add_option('-c', '--python-command', dest='python',\
    help='Python command to use on this system')
parser.add_option('-p', '--project-name', dest='projectname',\
    help='Name of the new project')
parser.add_option('-d', '--directory', dest='projectdirectory',\
    help='Folder to install project to')
parser.add_option('-g', '--git-repo', dest='gitrepo',\
    help='Location of bare git repo for this project')
(options, args) = parser.parse_args()

# Set project vars
if options.projectname == None:
    sys.exit('No Project Name specified. Use -p or --project-name= option flags to set this')

if options.python == None:
    python = 'python'
else:
    python = options.python

if options.projectdirectory == None:
    projectdirectory = defaultdirectory
else:
    projectdirectory = options.projectdirectory
fullprojectdirectory = "%s/%s/" % (projectdirectory, options.projectname)

if options.gitrepo == None:
    gitrepo = defaultrepo
else:
    gitrepo = options.gitrepo
fullgitrepo = "%s/%s/" % (gitrepo, options.projectname)
mediaurlfolder = options.projectname.capitalize() + 'Media'

# Get all required user input. Keep asking the questions until a valid answer
# is entered
boolchoices = (
    'yes', 'y', 'no', 'n'
)
yeschoices = ('yes', 'y')
includeenv = False
while True:
    env = raw_input('Should this site use VirtualEnv? (yes or no): ')
    if env.lower() in boolchoices:
        if env.lower() in yeschoices:
            includeenv = True
        break
vhostfolder = raw_input('What is the apache root (leave blank for /etc/apache2/): ')
binpath = raw_input('What is the path to the apache bin to restart? (Leave blank for /etc/init.d/apache2): ')
projecturl = raw_input("What will the site url be? (Don't include 'http://'): ")
mediaurl = raw_input('What is the media url? (Leave blank for http://media.' + projecturl + '/): ')
if mediaurl == '':
    mediaurl = 'media.' + projecturl
adminmediaurl = raw_input("What is the admin media url? (Leave blank for '" + mediaurl + "/admin/'): ")
if adminmediaurl == '':
    adminmediaurl = mediaurl + '/admin/'
dbbackend = raw_input('Which database backend are you going to use?: ')
dbname = raw_input('What is the name of the database? (Leave blank for ' + options.projectname + '): ')
if dbname == '':
    dbname = options.projectname
dbuser = raw_input('What is the database user name? (Leave blank for ' + options.projectname + '): ')
if dbuser == '':
    dbuser = options.projectname
dbpass = getpass.getpass('What is the database password?: ')
includecms = False
while True:
    cms = raw_input('Do you want to include Django CMS? (yes or no): ')
    if cms.lower() in boolchoices:
        if cms.lower() in yeschoices:
            includecms = True
        break
includeblog = False
while True:
    blog = raw_input('Include the blog? (yes or no): ')
    if blog.lower() in boolchoices:
        if blog.lower() in yeschoices:
            includeblog = True
        break

currentdir = os.getcwd()

# Set up the git repo
os.chdir(gitrepo)
os.mkdir(options.projectname)
os.chdir(fullgitrepo)
subprocess.Popen(['git', 'init', '--bare'])

# start the project in the specified project directory
os.chdir(projectdirectory)
subprocess.call(['django-admin.py', 'startproject', options.projectname])
# and place the project under git
os.chdir(fullprojectdirectory)
subprocess.call(['git', 'init'])
# now add the create repo as a remote for this project
subprocess.call(['git', 'remote', 'add', 'origin', fullgitrepo])
# write the initial git ignore file
gitignores = (
    '*.pyc',
    options.projectname + '/localsettings.py'
)
gitignorefile = open(fullprojectdirectory + '.gitignore', 'w')
gitignorefile.write("\n".join(gitignores))
gitignorefile.close()
# perform an initial commit and push so that the remote recognises the master ref later
os.chdir(fullprojectdirectory)
subprocess.call(['git', 'add', '.'])
subprocess.call(['git', 'commit', '-m', '"Initial commit"'])
subprocess.call(['git', 'push', 'origin', 'master'])

# Start up a virtualenv if required
if includeenv:
    # All that virtualenv does is sets a special sys.path for python so that
    # it doesn't use the default paths, just the newly set up virtual env
    # Easiest way to set up virtual env here is to manually duplicate that
    os.chdir(projectdirectory)
    subprocess.call(['virtualenv', '--no-site-packages', 'ENV'])
    oldpath = sys.path

    envbase = os.path.join(projectdirectory, 'ENV', 'lib',\
        'python%s' % sys.version[:3])
    sitebase = os.path.join(envbase, 'site-packages')
    oldpath = list(sys.path)
    newpath = [

        os.path.join(sitebase, 'setuptools-0.6c11-py2.6.egg'),
        os.path.join(sitebase, 'pip-0.8.1-py2.6.egg'),
        os.path.join(projectdirectory, 'ENV', 'lib', 'python26.zip'),
        os.path.join(envbase),
        os.path.join(envbase, 'plat-linux2'),
        os.path.join(envbase, 'lib-tk'),
        os.path.join(envbase, 'lib-old'),
        os.path.join(envbase, 'lib-dynload'),
        '/usr/lib/python2.6',
        '/usr/lib/python2.6/plat-linux2',
        envbase,
    ]

    # Clear the sys.path and add these new paths to it so that our python
    # modules install into the virtualenv rather than the main module dir
    for item in sys.path:
        sys.path.remove(item)
    sys.path = newpath
    # Install the required modules
    subprocess.call(['sudo', 'pip', 'install', '-E', 'ENV', 'django==1.4'])
    subprocess.call(['sudo', 'pip', 'install', '-E', 'ENV', 'django-admin-tools==0.4.0'])
    subprocess.call(['sudo', 'pip', 'install', '-E', 'ENV', 'south'])
    subprocess.call(['sudo', 'pip', 'install', '-E', 'ENV', 'django-tinymce'])
    # Install the optional modules, if they are wanted
    if includecms:
        subprocess.call(['sudo', 'pip', 'install', '-E', 'ENV', 'django-cms==2.3'])

# Add any bespoke apps
if includeblog:
    untarblog = subprocess.call(['tar', '-xvzf', currentdir + '/blog.tar.gz', '-C',\
        fullprojectdirectory + options.projectname])
    bafile = open(fullprojectdirectory + options.projectname + '/blog/admin.py')
    bloga = bafile.read()
    bafile.close()
    newbafile = open(fullprojectdirectory + options.projectname + '/blog/admin.py.tmp', "w")
    newbloga = bloga.replace('[~projectname~]', options.projectname)
    newbafile.write(newbloga)
    newbafile.close()

    bffile = open(fullprojectdirectory + options.projectname + '/blog/forms.py')
    blogf = bffile.read()
    bffile.close()
    newbffile = open(fullprojectdirectory + options.projectname + '/blog/forms.py.tmp', "w")
    newblogf = blogf.replace('[~projectname~]', options.projectname)
    newbffile.write(newblogf)
    newbffile.close()

    bmfile = open(fullprojectdirectory + options.projectname + '/blog/models.py')
    blogm = bmfile.read()
    bmfile.close()
    newbmfile = open(fullprojectdirectory + options.projectname + '/blog/models.py.tmp', "w")
    newblogm = blogm.replace('[~projectname~]', options.projectname)
    newbmfile.write(newblogm)
    newbmfile.close()

# Edit urls.py
urlsfile = ("%s%s/%s" % (fullprojectdirectory, options.projectname, 'urls.py'))
try:
    uf = open(urlsfile)
    urls = uf.read()
    uf.close()
except:
    sys.exit("Couldn't open url file - " + urlsfile)
urls = urls.replace("# from django.contrib import admin", "from django.contrib import admin")
urls = urls.replace("# admin.autodiscover()", "admin.autodiscover()")
urls = urls.replace("# url(r'^admin/', include(admin.site.urls)),", "url(r'^admin/', include(admin.site.urls)),")
upattern = r'^urlpatterns\s=\spatterns\(.*\)$'
fullurls = re.search(upattern, urls, re.MULTILINE | re.DOTALL).group(0)
urllist = fullurls.split("\n")
lasturl = urllist.pop()
# Add urls for default apps
urllist.append("    (r'^admin_tools/', include('admin_tools.urls')),")
urllist.append("")
if includeblog:
    urllist.append("    url(r'^blog/', include('" + options.projectname + ".blog.urls')),")
if includecms:
    urllist.append("    url(r'^', include('cms.urls')),")
# Write the new urls file
urllist.append(")")
newfullurls = "\n".join(urllist)
urls = urls.replace(fullurls, newfullurls)
uf = open(urlsfile, "w")
uf.write(urls)
uf.close()

# Get the settings and amend as necessary
settingsfile = ("%s%s/%s" % (fullprojectdirectory, options.projectname, 'settings.py'))
localsettingsfile = ("%s%s/%s" % (fullprojectdirectory, options.projectname, 'localsettings.py'))

sf = open(settingsfile)
settings = sf.read()
sf.close()

# Remove the items we use for local settings to their own file
localstart = settings.find('DEBUG')
localend = settings.find('# List of callables')
localsettings = settings[localstart:localend]
settings = settings.replace(localsettings, '')
localsettings = localsettings.replace("TIME_ZONE = 'America/Chicago'", "TIME_ZONE = 'Europe/London'")
localsettings = localsettings.replace("LANGUAGE_CODE = 'en-us'", "LANGUAGE_CODE = 'en-gb'")
# Add items for Django CMS to start of settings
settingsstart = settings.find('# List of callables')
settings = settings[:settingsstart] + "from localsettings import *\nimport os\ngettext = lambda s:s\n\n" + settings[settingsstart:]
settings = settings.replace("# 'django.contrib.admin',", "'django.contrib.admin',")
# Use regex to get the MIDDLEWARE_CLASSES
mpattern = r'^MIDDLEWARE_CLASSES\s=\s\(.*?\)$'
middleware = re.search(mpattern, settings, re.MULTILINE | re.DOTALL).group(0)
mlist = middleware.split("\n")
lastm = mlist.pop()
# Add bespoke middleware classes
if includecms:
    mlist.append("    'cms.middleware.multilingual.MultilingualURLMiddleware',")
    mlist.append("    'cms.middleware.page.CurrentPageMiddleware',")
    mlist.append("    'cms.middleware.user.CurrentUserMiddleware',")
    mlist.append("    'cms.middleware.toolbar.ToolbarMiddleware',")

#Use regex to get TEMPLATE_DIRS
tpattern = r'^TEMPLATE_DIRS\s=\s\(.*?\)$'
template = re.search(tpattern, settings, re.MULTILINE | re.DOTALL).group(0)
tlist = template.split("\n")
lastt = tlist.pop()
# Add default template directory
tlist.append("    '" + fullprojectdirectory + "template/',")

# Use regex to get the INSTALLED_APPS
ipattern = r'^INSTALLED_APPS\s=\s\(.*?\)$'
installedapps = re.search(ipattern, settings, re.MULTILINE | re.DOTALL).group(0)
ialist = installedapps.split("\n")
lastia = ialist.pop()

# Add admin tools. These need to be the first items in the INSTALLED_APPS
# tuple, so we need to reverse the list, add the items and reverse it back to
# it's original order again
ialist.reverse()
firstia = ialist.pop()
ialist.append("    'admin_tools.dashboard',")
ialist.append("    'admin_tools.menu',")
ialist.append("    'admin_tools.theming',")
ialist.append("    'admin_tools',")
ialist.append(firstia)
ialist.reverse()

# Add default apps
ialist.append("    'south',")
ialist.append("    'tinymce',")
# Add bespoke apps
if includecms:
    ialist.append("    'cms',")
    ialist.append("    'mptt',")
    ialist.append("    'menus',")
    ialist.append("    'sekizai',")
    ialist.append("    'cms.plugins.snippet',")
    ialist.append("    'cms.plugins.text',")
    # Set the CMS_TEMPLATES
    ctemplates = [
        "CMS_TEMPLATES = (",
        "     ('main_left_cms.html', 'Default'),",
        ")"
    ]
if includeblog:
    ialist.append("    '" + options.projectname + ".blog',")

# Set the languages
languages = [
    "LANGUAGES = [",
    "    ('en', 'English'),",
    "]"
]

# Set the template context processors
context = [
    "TEMPLATE_CONTEXT_PROCESSORS = (",
    "    'django.core.context_processors.auth',",
    "    'django.core.context_processors.i18n',",
    "    'django.core.context_processors.request',",
    "    'django.core.context_processors.media',"
]
if includecms:
    context.append("    'cms.context_processors.media',")
    context.append("    'sekizai.context_processors.sekizai'")
context.append(")")

# Re-write settings file
mlist.append(lastm)
newmiddleware = "\n".join(mlist)
settings = settings.replace(middleware, newmiddleware)

tlist.append(lastt)
newtemplate = "\n".join(tlist)
settings = settings.replace(template, newtemplate)

ialist.append(lastia)
newinstalledapps = "\n".join(ialist)
settings = settings.replace(installedapps, newinstalledapps)

settings += "\n".join(context) + "\n"
if includecms:
    settings += "\n".join(ctemplates) + "\n"
settings += "\n".join(languages) + "\n"

# Add admin_tools dashboard
settings += "ADMIN_TOOLS_INDEX_DASHBOARD = '%s.dashboard.CustomIndexDashboard'" % (options.projectname) + "\n"
# Add tinymce constants
settings += "\nTINYMCE_JS_URL = MEDIA_URL + 'js/tiny_mce/tiny_mce.js'\nTINYMCE_JS_ROOT = MEDIA_ROOT + 'js/tiny_mce'\n"

sf = open(settingsfile, "w")
sf.write(settings)
sf.close()

# Write the local settings file
lf = open(localsettingsfile, "w")
# Get and add values for local settings file
localsettings = localsettings.replace("MEDIA_ROOT = ''", "MEDIA_ROOT = '" + fullprojectdirectory + "media/'")
if dbbackend != '':
    localsettings = localsettings.replace("'django.db.backends.'", "'django.db.backends." + dbbackend + "'")
# Add the option to database settings to force storage engine to MyISAM as
# django-cms won't migrate correctly if INNODB is being used
localsettings = localsettings.replace(" 'NAME':", " 'OPTIONS': {'init_command': 'SET storage_engine=MYISAM'},\n        'NAME':")
if dbname != '':
    localsettings = localsettings.replace("'NAME': ''", "'NAME': '" + dbname + "'")
if dbuser != '':
    localsettings = localsettings.replace("'USER': ''", "'USER': '" + dbuser + "'")
if dbpass != '':
    localsettings = localsettings.replace("'PASSWORD': ''", "'PASSWORD': '" + dbpass + "'")
if includecms:
    localstatic = [
        fullprojectdirectory + "static/",
        '/static/',
    ]
    addstaticlink = subprocess.call(['ln', '-s', fullprojectdirectory + 'media/', fullprojectdirectory + 'static'])
else:
    # Replace the static placeholder with blank seeing as CMS isn't being used
    localstatic = []
localsettings = localsettings.replace('[~staticmediaplaceholder~]', "\n".join(localstatic))
if mediaurl == '':
    mediaurl = 'media.' + projecturl
localsettings = localsettings.replace("MEDIA_URL = ''", "MEDIA_URL = 'http://" + mediaurl + "/'")
# Add the settings for staticfiles
localsettings = localsettings.replace("STATIC_ROOT = ''", "STATIC_ROOT = '" + fullprojectdirectory + "static/'")
if adminmediaurl == '':
    adminmediaurl = mediaurl + '/admin/'
localsettings = localsettings.replace("ADMIN_MEDIA_PREFIX = '/media/'", "ADMIN_MEDIA_PREFIX = 'http://" + adminmediaurl + "'")

lf.write(localsettings)
lf.close()

# Un-tar the cms base templates
untartemplates = subprocess.call(['tar', '-xvzf', currentdir + '/template.tar.gz', '-C',\
    fullprojectdirectory])

# Un-tar the default media
untarmedia = subprocess.call(['tar', '-xvzf', currentdir + '/media.tar.gz', '-C',\
    fullprojectdirectory])

# Add our default custom libraries
untarlibs = subprocess.call(['tar', '-xvzf', currentdir + '/lib.tar.gz', '-C',\
    fullprojectdirectory + options.projectname])
thumbsfile = open(fullprojectdirectory + options.projectname + '/lib/thumbs.py')
thumbs = thumbsfile.read()
newthumbs = thumbs.replace('[~projectname~]', options.projectname)
newthumbsfile = open(fullprojectdirectory + options.projectname + '/lib/thumbs.py.tmp', "w")
newthumbsfile.write(newthumbs)
newthumbsfile.close()

# Re-writingthe thumbs file here
os.rename(fullprojectdirectory + options.projectname + '/lib/thumbs.py.tmp', fullprojectdirectory + options.projectname + '/lib/thumbs.py')

# Set up the database
os.chdir(fullprojectdirectory + options.projectname)

# Add any bespoke apps
if includeblog:
    untarblog = subprocess.call(['tar', '-xvzf', currentdir + '/blog.tar.gz', '-C',\
        fullprojectdirectory + options.projectname])
    bafile = open(fullprojectdirectory + options.projectname + '/blog/admin.py', 'w+')
    bloga = bafile.read()
    newbloga = bloga.replace('[~projectname~]', options.projectname)
    bafile.write(newbloga)
    bafile.close()
    bffile = open(fullprojectdirectory + options.projectname + '/blog/forms.py', 'w+')
    blogf = bffile.read()
    newblogf = blogf.replace('[~projectname~]', options.projectname)
    bffile.write(newblogf)
    bffile.close()
    bmfile = open(fullprojectdirectory + options.projectname + '/blog/models.py', 'w+')
    blogm = bmfile.read()
    newblogm = blogm.replace('[~projectname~]', options.projectname)
    bmfile.write(newblogm)
    bmfile.close()
    # Re-writing the blog files here as it didn't work correctly at the
    # blog creation stage
    os.rename(fullprojectdirectory + options.projectname + '/blog/admin.py.tmp',\
        fullprojectdirectory + options.projectname + '/blog/admin.py')
    os.rename(fullprojectdirectory + options.projectname + '/blog/forms.py.tmp',\
        fullprojectdirectory + options.projectname + '/blog/forms.py')
    os.rename(fullprojectdirectory + options.projectname + '/blog/models.py.tmp',\
        fullprojectdirectory + options.projectname + '/blog/models.py')
    os.chdir(fullprojectdirectory)
    print 'Full dir is %s' % fullprojectdirectory
    print "we're now in %s" % os.getcwd()
    blogsm = subprocess.call([python, 'manage.py', 'schemamigration', 'blog', '--initial'])
    #blogtempcommand = "tar -xvzf " + currentdir + "/blogtemplate.tar.gz -C " + projectdirectory + "template/"
    untarblogtemplate = subprocess.call(['tar', '-xvzf',\
        currentdir + '/blogtemplate.tar.gz', '-C',\
            fullprojectdirectory + 'template/'])
sync = subprocess.call([python, 'manage.py', 'syncdb'])

migrate = subprocess.call([python, 'manage.py', 'migrate'])

# Add the custom dashboard
dash = subprocess.call([python, 'manage.py', 'customdashboard'])

# Create the vhost entry for this site
if vhostfolder == '':
    vhostfolder = '/etc/apache2/'
vf = open(currentdir + '/template.vhost')
vhost = vf.read()
newvhost = vhost.replace('[~projectname~]',\
    options.projectname).replace('[~projecturl~]', projecturl)
vhostfile = open(projecturl, 'w')
vhostfile.write(newvhost)
vhostfile.close()
enablevhost = subprocess.call(['sudo', 'mv',\
    projecturl, vhostfolder + 'sites-available/'])
# Media vhost
if mediaurl != '':
    mvf = open(currentdir + '/mediatemplate.vhost')
    mvhost = mvf.read()
    newmvhost = mvhost.replace('[~projectdirectory~]',\
        fullprojectdirectory).replace('[~mediaurl~]', mediaurl)
    mvhostfile = open(mediaurl, 'w')
    mvhostfile.write(newmvhost)
    mvhostfile.close()
    enablemvhost = subprocess.call(['sudo', 'mv', mediaurl,\
        vhostfolder + 'sites-available/'])
    menhost = subprocess.call(['sudo', 'ln', '-s', vhostfolder +\
        'sites-available/' + mediaurl, vhostfolder + 'sites-enabled/' + mediaurl])

# Enable the site in apache
enhost = subprocess.call(['sudo', 'ln', '-s', vhostfolder + 'sites-available/'\
    + projecturl, vhostfolder + 'sites-enabled/' + projecturl])
if binpath == '':
    binpath = '/etc/init.d/apache2'
restartapache = subprocess.call(['sudo', binpath, 'restart'])

# Write the django wsgi file
djfile = open(currentdir + '/django.wsgi')
djwsgi = djfile.read()
newdjwsgi = djwsgi.replace('[~projectname~]', options.projectname)
newdjwsgi = newdjwsgi.replace('[~projectdirectory~]', fullprojectdirectory)
# Add the script required for using virtualenv if needed
if includeenv:
    velist = [
        "vepath = '" + sitebase + "'",
        "prev_sys_path = list(sys.path)",
        "site.addsitedir(vepath)",
        "# reorder sys.path so new directories from the addsitedir show up first",
        "new_sys_path = [p for p in sys.path if p not in prev_sys_path]",
        "for item in new_sys_path:",
        "    sys.path.remove(item)",
        "sys.path[:0] = new_sys_path",
    ]
    vetext = "\n".join(velist) + "\n"
else:
    vetext = ''
newdjwsgi = newdjwsgi.replace('[~vetext~]', vetext)
newdjfile = open(fullprojectdirectory + '/django.wsgi', 'w')
newdjfile.write(newdjwsgi)
newdjfile.close()

os.chdir(currentdir)

if includeenv:
    for item in sys.path:
        sys.path.remove(item)
    sys.path = oldpath

"""
pattern = r'^INSTALLED_APPS\s=\s\(.*?\)$'
"""
