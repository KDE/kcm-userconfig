# -*- coding: utf-8 -*-

#############################################################################
##
## Copyright 2004-2006 Simon Edwards <simon@simonzone.com>
## Copyright 2011 Romain Perier <romain.perier@gmail.com>
##
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of
## the License, or (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.
##
#############################################################################

import fcntl
import os
import os.path
from context import *

def LockFDRead(fd):
    retries = 6
    while retries!=0:
        try:
            fcntl.lockf(fd,fcntl.LOCK_SH | fcntl.LOCK_NB)
            return True
        except IOError:
            # Wait a moment
            time.sleep(1)
    return False

def LockFDWrite(fd):
    retries = 6
    while retries!=0:
        try:
            fcntl.lockf(fd,fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except IOError:
            # Wait a moment
            time.sleep(1)
    return False

def UnlockFD(fd):
    fcntl.lockf(fd,fcntl.LOCK_UN)

def createTempFile(origfile):
    origstat = os.stat(origfile)
    tmp_prefix = os.path.basename(origfile) + "."
    tmp_dir = os.path.dirname(origfile)
    try:
        ret = tempfile.mkstemp(prefix=tmp_prefix, dir=tmp_dir)
    except:
        raise IOError, "Unable to create a new temporary file for " + origfile
    (fd, tmpfile) = ret
    shutil.copymode(origfile, tmpfile)
    os.chown(tmpfile, origstat.st_uid, origstat.st_gid)

    return ret

class PwdContext(Context):
    #def __init__(self,editmode,passwordfile="etc-passwd",groupfile='etc-group',shadowfile="etc-shadow"):
    def __init__(self, editmode, passwordfile="/etc/passwd", groupfile="/etc/group", gshadowfile="/etc/gshadow", shadowfile="/etc/shadow"):
        Context.__init__(self)
        self.__editmode = editmode
        self.__passwordfile = passwordfile
        self.__groupfile = groupfile
        self.__gshadowfile = gshadowfile
        self.__shadowfile = shadowfile
        self._setDefaultValues()

        # Read in the password file
        fhandle = codecs.open(passwordfile,'r',locale.getpreferredencoding())
        if LockFDRead(fhandle.fileno())==False:
            raise IOError,"Unable to lock the "+passwordfile+" file."
        try:
            for line in fhandle.readlines():
                if line.strip()!="":
                    newuserobj = self.newUser(False)
                    newuserobj._initString(line)
                    self._users.append(newuserobj)
        finally:
            UnlockFD(fhandle.fileno())
            fhandle.close()

        # Read the group file
        fhandle = codecs.open(groupfile,'r',locale.getpreferredencoding())
        if LockFDRead(fhandle.fileno())==False:
            raise IOError,"Unable to lock the "+groupfile+" file."
        try:
            for line in fhandle.readlines():
                if line.strip()!="":
                    newgroupobj = self.newGroup(False)
                    newgroupobj._initString(line)
                    self._groups.append(newgroupobj)
        finally:
            UnlockFD(fhandle.fileno())
            fhandle.close()
        if self.__editmode:
            # Load up the info from the shadow file too.
            fhandle = codecs.open(shadowfile,'r',locale.getpreferredencoding())
            if LockFDRead(fhandle.fileno())==False:
                raise IOError,"Unable to lock the "+shadowfile+" file."
            try:
                for line in fhandle.readlines():
                    if line.strip()!="":
                        try:
                            (username,encpass,passlastchange,passminimumagebeforechange,passmaximumage, \
                                passexpirewarn,passexpiredisabledays,disableddays,reserve) = \
                                tuple(line.strip().split(":"))
                            userobj = self.lookupUsername(username)
                            if userobj is not None:
                                if encpass=="":
                                    encpass = u"*"
                                userobj._encpass = encpass
                                if userobj._encpass[0]=='!':
                                    userobj._islocked = True
                                    userobj._encpass = userobj._encpass[1:]
                                else:
                                    userobj._islocked = False
                                # FIXME : set time
                                if passlastchange and passlastchange!=u"None":
                                    userobj._passlastchange = int(passlastchange)
                                else:
                                    passlastchange = 0

                                if passminimumagebeforechange=="":
                                    passminimumagebeforechange = None
                                else:
                                    passminimumagebeforechange = int(passminimumagebeforechange)
                                    if passminimumagebeforechange>=99999:
                                        passminimumagebeforechange = None
                                userobj._passminimumagebeforechange = passminimumagebeforechange

                                if passmaximumage=="":
                                    passmaximumage = None
                                else:
                                    passmaximumage = int(passmaximumage)
                                    if passmaximumage>=99999:
                                        passmaximumage = None
                                userobj._passmaximumage = passmaximumage

                                if passexpirewarn=="":
                                    passexpirewarn = None
                                else:
                                    passexpirewarn = int(passexpirewarn)
                                    if passexpirewarn>=99999:
                                        passexpirewarn = None
                                userobj._passexpirewarn = passexpirewarn

                                if passexpiredisabledays=="":
                                    userobj._passexpiredisabledays = None
                                else:
                                    userobj._passexpiredisabledays = int(passexpiredisabledays)

                                if disableddays=="" or disableddays==u"99999":
                                    userobj._disableddays = None
                                else:
                                    userobj._disableddays = int(disableddays)

                                userobj._reserve = reserve
                            else:
                                print "Couldn't find",username
                        except ValueError:
                            pass
            finally:
                UnlockFD(fhandle.fileno())
                fhandle.close()

        for group in self._groups:
            group.polish()
        for user in self._users:
            user.polish()

    def _createUser(self):
        return PwdUser(self)

    def _createGroup(self):
        return PwdGroup(self)

    def save(self):
        if self.__editmode==False:
            raise IOError, "Can't save, the context was created Read only."

        self._sanityCheck()

        # Write out the new password file.        
        (fd, tmpname) = createTempFile(self.__passwordfile)
        for u in self._users:
            os.write(fd, u._getPasswdEntry().encode(locale.getpreferredencoding(),'replace'))
            #print u._getPasswdEntry()
        os.close(fd)

        # Update the passwd file
        passwordlock = os.open(self.__passwordfile, os.O_WRONLY) # FIXME encoding
        if LockFDWrite(passwordlock)==False:
            raise IOError,"Couldn't get a write lock on "+self.__passwordfile
        try:
            os.rename(tmpname, self.__passwordfile)
        finally:
            UnlockFD(passwordlock)
            os.close(passwordlock)

        # Write out the new group file
        (fd, tmpname) = createTempFile(self.__groupfile)
        origstat = os.stat(self.__groupfile)
        for g in self._groups:
            os.write(fd,g._getGroupFileEntry().encode(locale.getpreferredencoding()))
            #print g._getGroupFileEntry()[:-1]
        os.close(fd)
        os.chown(tmpname, origstat.st_uid, origstat.st_gid)

        # Update the group file.
        grouplock = os.open(self.__groupfile, os.O_WRONLY)
        if LockFDWrite(grouplock)==False:
            raise IOError,"Couldn't get write lock on "+self.__groupfile
        try:
            os.rename(tmpname, self.__groupfile)
        finally:
            UnlockFD(grouplock)
            os.close(grouplock)

        # Write out the new gshadow file
        (fd, tmpname) = createTempFile(self.__gshadowfile)
        origstat = os.stat(self.__gshadowfile)
        for g in self._groups:
            os.write(fd,g._getGShadowFileEntry().encode(locale.getpreferredencoding()))
        os.close(fd)
        os.chown(tmpname, origstat.st_uid, origstat.st_gid)

        # Update the gshadow file.
        gshadowlock = os.open(self.__gshadowfile, os.O_WRONLY)
        if LockFDWrite(gshadowlock)==False:
            raise IOError,"Couldn't get write lock on "+self.__gshadowfile
        try:
            os.rename(tmpname, self.__gshadowfile)
        finally:
            UnlockFD(gshadowlock)
            os.close(gshadowlock)

        # Write out the new shadow file
        origstat = os.stat(self.__shadowfile)
        (fd, tmpname) = createTempFile(self.__shadowfile)
        for u in self._users:
            os.write(fd,u._getShadowEntry().encode(locale.getpreferredencoding()))
            #print u._getShadowEntry()[:-1]
        os.close(fd)

        # Update the shadow file.

        # Make sure that it is writable.
        if (origstat.st_mode & stat.S_IWUSR)==0:
            os.chmod(self.__shadowfile,origstat.st_mode|stat.S_IWUSR)

        shadowlock = os.open(self.__shadowfile, os.O_WRONLY)
        if LockFDWrite(shadowlock)==False:
            raise IOError,"Couldn't get write lock on "+self.__shadowfile
        try:
            os.rename(tmpname, self.__shadowfile)
        finally:
            UnlockFD(shadowlock)
            os.close(shadowlock)

        # set the permissions back to thier default.
        if (origstat.st_mode & stat.S_IWUSR)==0:
            os.chmod(self.__shadowfile,origstat.st_mode)

###########################################################################
class PwdUser(UnixUser):
    def __init__(self,context):
        UnixUser.__init__(self,context)
        self._reserve = u""

    def _initString(self,line):
        (self._username,x,self._uid,self._gid,self._gecos,self._homedirectory, \
            self._loginshell) =  tuple(line.strip().split(":"))
        self._uid = int(self._uid)
        self._gid = int(self._gid)

    def _getPasswdEntry(self):
        return u":".join( [self._username,
            u"x",
            unicode(self._uid),
            unicode(self._primarygroup.getGID()),
            self._gecos,
            self._homedirectory,
            self._loginshell ] ) + u"\n"

    def _getShadowEntry(self):
        if self._islocked:
            encpass = u'!' + self._encpass
        else:
            encpass = self._encpass

        if self._passminimumagebeforechange==None:
            passminimumagebeforechange = ""
        else:
            passminimumagebeforechange = str(self._passminimumagebeforechange)

        if self._passmaximumage==None:
            passmaximumage = u"99999"
        else:
            passmaximumage = unicode(self._passmaximumage)

        if self._disableddays==None:
            disableddays = u""
        else:
            disableddays = unicode(self._disableddays)

        if self._passexpiredisabledays==None:
            passexpiredisabledays = u""
        else:
            passexpiredisabledays = unicode(self._passexpiredisabledays)

        if self._passexpirewarn==None:
            passexpirewarn = u""
        else:
            passexpirewarn = unicode(self._passexpirewarn)

        return u":".join( [self._username,
            encpass,
            unicode(self._passlastchange),
            passminimumagebeforechange,
            passmaximumage,
            passexpirewarn,
            passexpiredisabledays,
            disableddays,
            self._reserve ])+ u"\n"

###########################################################################
class PwdGroup(UnixGroup):
    def __init__(self,context):
        UnixGroup.__init__(self,context)
        self._memberids = u""
        self._encpass = u""

    def _initString(self,line):
        (self._groupname,self._encpass,self._gid,self._memberids) = tuple(line.strip().split(":"))
        self._gid = int(self._gid)

    def polish(self):
        membernames = self._memberids.split(",")
        for username in membernames:
            userobj = self._context.lookupUsername(username)
            if userobj!=None:
                self._members.append(userobj)

    def _getGroupFileEntry(self):
        return u":".join( [ self._groupname,
            self._encpass,
            unicode(self._gid),
            u",".join([u.getUsername() for u in self._members if u.getPrimaryGroup() is not self])]) + u"\n"
    def _getGShadowFileEntry(self):
        return u":".join( [ self._groupname, "!", "",
            u",".join([u.getUsername() for u in self._members if u.getPrimaryGroup() is not self])]) + u"\n"


