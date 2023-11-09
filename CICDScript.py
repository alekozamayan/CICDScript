from abc import ABC, abstractmethod
import xml.etree.ElementTree as ET
import shutil
import shlex
import os
import argparse
import sys
import re
import subprocess
import locale
import glob
from datetime import datetime

EXIT_SUCCESS = 0
EXIT_FAILURE = 1

streams = {"stderr": sys.stderr}
processStreams = {}


# \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# Version Control System (VCS) class definitions --------------------------------------------------------
# \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

# VCS Interface class

class VCSInterface(ABC):

    @abstractmethod
    def __init__(self, vcs_user: str = None, vcs_pass: str = None):
        pass

    # Check given URL if it is a VCS URL or not
    @abstractmethod
    def URLCheck(self, path: str) -> bool:
        pass

    # Export a directory from VCS to file path
    @abstractmethod
    def vcs_export(self, vcs_srcurl: str, file_dest: str, *args) -> str:
        pass

    # Import a directory to VCS repository path
    @abstractmethod
    def vcs_import(self, vcs_desturl: str, file_src: str, logmessage: str = " ", *args) -> str:
        pass

    # Copy a directory inside a VCS repo to another VCS repo path
    @abstractmethod
    def vcs_copy(self, vcs_srcurl: str, vcs_desturl: str, logmessage: str = " ", *args) -> str:
        pass

    # Return a list of all files inside a VCS repo
    @abstractmethod
    def vcs_list(self, vcs_url: str, *args) -> list:
        pass


# Apache SVN (Subversion) Client Controller class

class SVNController(VCSInterface):
    __urlregex = re.compile(r'^(?:(?:http|ftp)s?://|file:///)')
    __svncommonargs = ["--non-interactive", "--trust-server-cert-failures=unknown-ca"]

    def __init__(self, vcs_user: str = None, vcs_pass: str = None):
        super().__init__(vcs_user=vcs_user, vcs_pass=vcs_pass)
        self.__svnauthargs = list()

        # crease svn authorization argument list here
        if vcs_user:
            self.__svnauthargs += ['--username', vcs_user]
            if vcs_pass:
                self.__svnauthargs += ['--password', vcs_pass]

    def URLCheck(self, path: str) -> bool:
        return re.match(self.__urlregex, path) is not None

    def vcs_export(self, vcs_srcurl: str, file_dest: str, *args) -> str:
        subprocess.run(['svn', 'export', vcs_srcurl, file_dest, '--force']
                       + list(args)
                       + self.__svnauthargs
                       + self.__svncommonargs, check=True, **processStreams)
        return file_dest

    def vcs_import(self, vcs_desturl: str, file_src: str, logmessage: str = " ", *args) -> str:
        # Create a folder path with the basename of file_src folder path
        vcs_desturl = '/'.join([vcs_desturl, os.path.basename(file_src)])
        subprocess.run(['svn', 'import', file_src, vcs_desturl, '-m', f'{logmessage}']
                       + list(args) + self.__svnauthargs + self.__svncommonargs, check=True, **processStreams)
        return vcs_desturl

    def vcs_copy(self, vcs_srcurl: str, vcs_desturl: str, logmessage: str = " ", *args) -> str:
        subprocess.run(['svn', 'copy', vcs_srcurl, vcs_desturl, '-m', f'"{logmessage}"']
                       + list(args) + self.__svnauthargs + self.__svncommonargs, check=True, **processStreams)
        return vcs_desturl

    def vcs_list(self, vcs_url: str, *args) -> list:
        result = subprocess.run(['svn', 'ls', vcs_url] + list(args) + self.__svnauthargs + self.__svncommonargs,
                                check=True, stdout=subprocess.PIPE)
        # decode byte string before returning
        return result.stdout.decode(locale.getencoding()).splitlines()


# If intended to use another VCS client, create a new class
# complying with VCSInterface


# ////////////////////////////////////////////////////////////////////////////////////////////////////////
# -------------------------------------------------------------------------------------------------------
# //////////////////////////////////////////////////////////////////////////////////////////////////////

# \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# Copier class, managing all file transactions ----------------------------------------------------------
# \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

class Copier:

    def __init__(self, vcsObj: VCSInterface):
        self.__vcs = vcsObj

    # Copy paths inside VCS
    def __copyFromVCSToVCS(self, dest: str, src: str, logmessage: str) -> list:
        return [self.__vcs.vcs_copy(src, dest, logmessage)]

    # Export path from VCS repo to file system
    def __copyFromVCSToFS(self, dest: str, src: str, logmessage: str) -> list:
        return [self.__vcs.vcs_export(src, dest)]

    # Import matching paths to VCS repo
    def __copyFromFSToVCS(self, dest: str, src: str, logmessage: str) -> list:
        return [self.__vcs.vcs_import(dest, srcpath, logmessage) for srcpath in glob.glob(src)]

    # Operate on filesystem
    def __copyFromFSToFS(self, dest: str, src: str, logmessage: str) -> list:
        retlist = []

        # Check if 'dest' represents a directory path, which does not exist
        if (dest.endswith('/') or dest.endswith('\\')) and not os.path.isdir(dest):
            # Create that path
            os.mkdir(dest)

        # Check again, if the directory path exists
        if os.path.isdir(dest):
            for srcpath in glob.glob(src):
                if os.path.isdir(srcpath):
                    retlist.append(shutil.copytree(srcpath, os.sep.join([dest, os.path.basename(srcpath)]),
                                                    dirs_exist_ok=True))
                else:
                    retlist.append(shutil.copy(srcpath, dest))

        # If there is no directory path, treat 'dest' as a filename
        else:
            retlist.append(shutil.copy(glob.glob(src)[0], dest))

        return retlist

    # This is a lookup table to call suitable function according to 'dest' and 'src' types
    __functable = ((__copyFromFSToFS, __copyFromFSToVCS),
                   (__copyFromVCSToFS, __copyFromVCSToVCS))

    # This is the universal copy method, covering all directions.
    # it supports globbing in the file paths.
    def copy(self, dest: str, src: str, logmessage: str) -> list:
        return self.__functable[self.__vcs.URLCheck(src)][self.__vcs.URLCheck(dest)](self, dest, src, logmessage)

    # This method examines the deploy directory and generates a valid filename if
    # the name of the file to be deployed is already occupied. Otherwise returns
    # the original name.
    def getVacantName(self, path: str, name: str) -> str:

        rawNameList = self.__vcs.vcs_list(path) if self.__vcs.URLCheck(path) else os.listdir(path)
        namelist = [os.path.splitext(x)[0] for x in rawNameList if x.startswith(name)]

        # Check if the processed name in namelist, if so, add incrementer
        processedName = name
        incrementer = 2
        while processedName in namelist:
            processedName = name + f"_{incrementer}"
            incrementer += 1

        return processedName

# ////////////////////////////////////////////////////////////////////////////////////////////////////////
# -------------------------------------------------------------------------------------------------------
# //////////////////////////////////////////////////////////////////////////////////////////////////////


# \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# Config .XML File Node Processor Class Definitions -----------------------------------------------------
# \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

# Base Processor class, containing methods to process
# "dependency" and "buildExecutable" entries
class BaseProcessor:
    def __init__(self, mainNode: ET.Element, copierObj: Copier):
        self._copier = copierObj
        self.__mainNode = mainNode

    def __processDependency(self, dep: dict):
        # Copy the dependency
        self._copier.copy(dest=dep["dest"], src=dep["path"], logmessage="Copied from " + dep["path"])

    def __runExecutable(self, buildexec: dict):
        # Run the build scripts
        curdir = os.getcwd()
        try:
            # Get first glob match for a globbed executable path
            globbedPath = glob.glob(buildexec["path"])[0]
            # Change current directory to the executable path
            os.chdir(os.path.dirname(os.path.abspath(globbedPath)))
            execargs = buildexec["args"] if "args" in buildexec.keys() else ""
            lexer = shlex.shlex(instream=f'{os.path.basename(globbedPath)} {execargs}',
                                punctuation_chars=True)
            # Run executable
            subprocess.run(list(lexer), check=True, **processStreams)

        except Exception as e:
            print(e, file=streams["stderr"])
            sys.exit(EXIT_FAILURE)
        finally:
            # Turn back to the old cwd
            os.chdir(curdir)

    # This is the most generic process method type can be applied.
    # Any additions to this procedure should be made in the inheriting
    # class
    def process(self):
        for i in self.__mainNode.iter():
            if "dependency" == i.tag:
                self.__processDependency(i.attrib)
            elif "buildExecutable" == i.tag:
                self.__runExecutable(i.attrib)
            else:
                pass


# Deployer class, handling package deployment process
# in addition to BaseProcessor
class Deployer(BaseProcessor):
    def __init__(self, mainNode: ET.Element, copierObj: Copier, logmessage: str,
                 deployPathFile: str = None):
        super().__init__(mainNode=mainNode, copierObj=copierObj)
        # Pull deploy node attributes
        self.__packageName = mainNode.attrib["name"]
        self.__deployDest = mainNode.attrib["dest"]
        self.__deploySrc = mainNode.attrib["path"]
        self.__logmessage = logmessage
        self.__deployPathFile = deployPathFile

    def process(self):
        # Run base process first
        super().process()

        # Produce package name, format with datetime attributes
        processedPckgName = datetime.now().strftime(self.__packageName)
        # Check vacancy for this package name, if not, produce new one
        processedPckgName = self._copier.getVacantName(path=self.__deployDest, name=processedPckgName)
        # Make archive (zip) of the package contents
        processedPckgName = shutil.make_archive(base_name=processedPckgName, format='zip', root_dir=self.__deploySrc)
        # Deploy package
        destPathList = self._copier.copy(dest=self.__deployDest, src=processedPckgName, logmessage=self.__logmessage)

        # Write deploy paths to the file
        if self.__deployPathFile:
            with open(self.__deployPathFile, 'w') as deployfile:
                for i in destPathList:
                    deployfile.write(i)


# ////////////////////////////////////////////////////////////////////////////////////////////////////////
# -------------------------------------------------------------------------------------------------------
# //////////////////////////////////////////////////////////////////////////////////////////////////////

class MasterProcessor:

    def __init__(self):
        # Commands dict
        self.__commandDict = {'build': self.__processBuild,
                              'deploy': self.__processDeploy,
                              'all': self.__processAll}

        # Version Control System dict
        self.__vcsDict = {'svn': SVNController}

        # Parse arguments
        self.__parsedArgs = self.__parseArguments()

        # Obtain xml root node
        self.__xmlroot = self.__produceXMLRoot(self.__parsedArgs.configxml, self.__parsedArgs.extargs)

        # Create Copier object
        self.__copierObj = Copier(self.__vcsDict[self.__parsedArgs.vcs](
                                      self.__parsedArgs.vcsuser,
                                      self.__parsedArgs.vcspass))

    def processCommand(self):
        self.__commandDict[self.__parsedArgs.command]()

    # Argument parse method
    def __parseArguments(self):
        parser = argparse.ArgumentParser(description="CI/CD script", add_help=True)

        parser.add_argument('--version', action='version', version=f"{parser.description} 1.0.0")
        parser.add_argument('-v', '--verbose', action='store_true', dest='verbose', help='Verbose output.')

        parser.add_argument('--command', '-c', choices= self.__commandDict.keys(), default='all',
                            help='Specifies the process to be performed.')
        parser.add_argument('configxml', default='config.xml', help='The .xml file to be used for process.')

        parser.add_argument('--vcs', choices=self.__vcsDict.keys(), default='svn',
                            help='Specifies the version control system to be used to operate on remote repository URLs.')

        parser.add_argument('--deploypathfile', default=None, dest='deployPathFile',
                            help='If given, deploy path URL will be written to the file.')
        parser.add_argument('--extargs', nargs='*', help="""External arguments to be replaced in .xml file text:
           e.g. --extargs somekey1=someval1 somekey2=someval2
           will replace {somekey1} and {somekey2} instances in
           .xml file with someval1 and someval2.""")

        logGroup = parser.add_mutually_exclusive_group()
        logGroup.add_argument('-m', dest='logmessage', default=None, help='The log message used when deploying.')
        logGroup.add_argument('-F', dest='logfile', default=None, help='The log file contains log message.')

        authGroup = parser.add_argument_group('Authorization parameters for VCS access')
        authGroup.add_argument('--username', dest='vcsuser', help='User name')
        authGroup.add_argument('--passwd', dest='vcspass', help='User password')

        parsedArgs = parser.parse_args()

        # define output stream if verbose mode is on
        if parsedArgs.verbose:
            streams["stdout"] = sys.stdout
        else:
            processStreams["stdout"] = subprocess.DEVNULL

        return parsedArgs

    # XML Root extract method
    @staticmethod
    def __produceXMLRoot(xmlpath: str, extArgList: list) -> ET.Element:
        # Pull xml root node
        xmlroot = ET.parse(xmlpath).getroot()

        # Pull xml attributes
        refKeywords = xmlroot.attrib

        # Pull external arguments and obtain full reference dict
        if extArgList:
            refKeywords.update({x: y for x, y in (s.split('=') for s in extArgList)})

        # and replace if any reference given in .xml
        if len(refKeywords):
            for subnode in xmlroot.iter():
                if subnode.text:
                    subnode.text = subnode.text.format(**refKeywords)
                for key in subnode.attrib:
                    subnode.attrib[key] = subnode.attrib[key].format(**refKeywords)

        return xmlroot


    # Build command process method
    def __processBuild(self):
        BaseProcessor(mainNode=self.__xmlroot.find("build"), copierObj=self.__copierObj).process()

    # Deploy command process method
    def __processDeploy(self):
        logfile = self.__parsedArgs.logfile
        logmessage = self.__parsedArgs.logmessage
        deployPathFile = self.__parsedArgs.deployPathFile

        # Extract log message, from file or argument
        if logfile:
            with open(logfile, 'r') as f:
                parsedLogMessage = f.read()
        elif logmessage:
            parsedLogMessage = logmessage
        else:
            parsedLogMessage = "Default commit message"

        # Start deploy process
        Deployer(mainNode=self.__xmlroot.find("deploy"), copierObj=self.__copierObj,
                 logmessage=parsedLogMessage, deployPathFile=deployPathFile).process()

    # Method for processing all jobs at once
    def __processAll(self):
        self.__processBuild()
        self.__processDeploy()

# Main
if __name__ == '__main__':

    masterObj = MasterProcessor()
    masterObj.processCommand()

    # Exit with success code
    sys.exit(EXIT_SUCCESS)
