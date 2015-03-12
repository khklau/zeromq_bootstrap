import hashlib
import os
import shutil
import subprocess
import tarfile
import urllib
import zipfile
from waflib import Logs
from waflib.extras.preparation import PreparationContext
from waflib.extras.build_status import BuildStatus
from waflib.extras.filesystem_utils import removeSubdir
from waflib.extras.url_utils import tryDownload, syncRemoteFile

__downloadUrl = 'http://download.zeromq.org/%s'
__posixFile = 'zeromq-4.0.3.tar.gz'
__posixSha256Checksum = '\x57\xfa\x92\x05\xbd\xa2\x81\x3c\x6f\x76\x45\xd1\xd6\x01\x68\x38\xd2\x7b\xac\x83\x3c\x1e\xde\xba\xec\xc7\xf3\x62\x61\x44\x71\x1a'
__ntFile = 'zeromq-4.0.3.zip'
__ntSha256Checksum = '\x87\x54\x18\x8b\x0d\x11\x2f\xa4\x14\x83\x5e\xea\x0e\xf2\xfa\x24\xad\x3c\x27\x1c\x89\xf3\x04\x72\x88\x4e\x59\xec\x0d\x15\xdf\xae'
__cxxHeaderUrl = 'https://raw.githubusercontent.com/zeromq/cppzmq/master/%s'
__cxxHeaderFile = 'zmq.hpp'
__srcDir = 'src'

def options(optCtx):
    optCtx.load('dep_resolver')

def prepare(prepCtx):
    prepCtx.options.dep_base_dir = prepCtx.srcnode.find_dir('..').abspath()
    prepCtx.load('dep_resolver')
    status = BuildStatus.init(prepCtx.path.abspath())
    if status.isSuccess():
	prepCtx.msg('Preparation already complete', 'skipping')
	return
    if os.name == 'posix':
	filePath = os.path.join(prepCtx.path.abspath(), __posixFile)
	url = __downloadUrl % __posixFile
	sha256Checksum = __posixSha256Checksum
    elif os.name == 'nt':
	filePath = os.path.join(prepCtx.path.abspath(), __ntFile)
	url = __downloadUrl % __ntFile
	sha256Checksum = __ntSha256Checksum
    else:
	prepCtx.fatal('Unsupported OS %s' % os.name)
    prepCtx.msg('Synchronising', url)
    if syncRemoteFile(sha256Checksum, url, filePath):
	prepCtx.msg('Saved to', filePath)
    else:
	prepCtx.fatal('Synchronisation failed')
    extractDir = 'zeromq-4.0.3'
    removeSubdir(prepCtx.path.abspath(), __srcDir, extractDir, 'bin', 'lib', 'include')
    prepCtx.start_msg('Extracting files to')
    if os.name == 'posix':
	handle = tarfile.open(filePath, 'r:*')
	handle.extractall(prepCtx.path.abspath())
    elif os.name == 'nt':
	handle = zipfile.ZipFile(filePath, 'r')
	handle.extractall(prepCtx.path.abspath())
    else:
	prepCtx.fatal('Unsupported OS %s' % os.name)
    os.rename(extractDir, __srcDir)
    prepCtx.end_msg(os.path.join(prepCtx.path.abspath(), __srcDir))
    cxxHeaderPath = os.path.join(prepCtx.path.abspath(), __cxxHeaderFile)
    cxxHeaderUrl = __cxxHeaderUrl % __cxxHeaderFile
    if os.access(cxxHeaderPath, os.R_OK):
	prepCtx.start_msg('Using existing Cxx header file')
	prepCtx.end_msg(cxxHeaderPath)
    else:
	prepCtx.start_msg('Downloading %s' % cxxHeaderUrl)
	if tryDownload(cxxHeaderUrl, cxxHeaderPath, 10):
	    prepCtx.end_msg('Saved to %s' % cxxHeaderPath)
	else:
	    prepCtx.fatal('Could not download %s' % cxxHeaderUrl)

def configure(confCtx):
    confCtx.load('dep_resolver')
    status = BuildStatus.init(confCtx.path.abspath())
    if status.isSuccess():
	confCtx.msg('Configuration already complete', 'skipping')
	return
    srcPath = os.path.join(confCtx.path.abspath(), __srcDir)
    os.chdir(srcPath)
    if os.name == 'posix':
	returnCode = subprocess.call([
		'sh',
		os.path.join(srcPath, 'configure'),
		'--prefix=%s' % confCtx.srcnode.abspath(),
		'--enable-dependency-tracking',
		'--enable-static=yes',
		'--enable-shared=yes'])
	if returnCode != 0:
	    confCtx.fatal('Zeromq configure failed: %d' % returnCode)
    elif os.name == 'nt':
	# Nothing to do, just use the provided VS solution
	return
    else:
	confCtx.fatal('Unsupported OS %s' % os.name)

def build(buildCtx):
    status = BuildStatus.load(buildCtx.path.abspath())
    if status.isSuccess():
	Logs.pprint('NORMAL', 'Build already complete                   :', sep='')
	Logs.pprint('GREEN', 'skipping')
	return
    srcPath = os.path.join(buildCtx.path.abspath(), __srcDir)
    os.chdir(srcPath)
    if os.name == 'posix':
	returnCode = subprocess.call([
		'make',
		'install'])
    elif os.name == 'nt':
	returnCode = subprocess.call([
		'devenv.com',
		os.path.join(srcPath, 'builds', 'msvc', 'msvc10.sln')])
    else:
	confCtx.fatal('Unsupported OS %s' % os.name)
    if returnCode != 0:
	buildCtx.fatal('Zeromq build failed: %d' % returnCode)
    cxxHeaderTgt = os.path.join(buildCtx.path.abspath(), 'include', __cxxHeaderFile)
    if os.path.exists(cxxHeaderTgt):
	os.remove(cxxHeaderTgt)
    cxxHeaderSrc = os.path.join(buildCtx.path.abspath(), __cxxHeaderFile)
    if os.path.exists(cxxHeaderSrc):
	shutil.copy2(cxxHeaderSrc, os.path.join(buildCtx.path.abspath(), 'include'))
    status.setSuccess()
