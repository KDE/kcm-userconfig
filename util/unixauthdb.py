#!/usr/bin/python
# -*- coding: utf-8 -*-
###########################################################################
#    Copyright (C) 2004-2006 by Simon Edwards
#    <simon@simonzone.com>
#
# Copyright: See COPYING file that comes with this distribution
#
###########################################################################
# An API for querying and modifying the authorisation database on Unix systems.
#
# The first function that you need to use is getContext(). It returns a 
# Context object that contains all relevant information concerning 
# the current authorisation database on this machine.

import crypt
import random
import fcntl
import time
import os
import os.path
import stat
import shutil
import codecs
import locale
import tempfile

ldaperror = ""
try:
    import ldap 
except ImportError:
    ldaperror = "The LDAP Python Module is not installed, but needed to use LDAP. Install it."

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

def getContext(editmode=False):
    """Get a Context object describing the system's authorisation database.

    Parameters:

    editmode - Set to true if you also wish change the information in this
    context. Root access is required. Defaults to false.

    Returns a Context object.

    If the environmental variable "USERCONFIG_USES_LDAP" is set to "true",
    userconfig will use LDAP as the backend. This feature is in development
    and using it is not recommended, it won't work.
    """

    # Detect what kind of auth system we are running on and create
    # and initialise the corresponding Context object type.

    # Check for Mandrake

    # Check libuser.conf
    try:
        if os.environ["USERCONFIG_USES_LDAP"].lower() == "true":
            use_ldap = True 
    except KeyError,e:
        use_ldap = False
    if not use_ldap:
        return PwdContext(editmode)
    else:
        print "==================================================================="
        print "Warning:"
        print "\tYou are using LDAP as backend. This feature is under development"
        print "\tand it is currently not recommended to use it."
        print "\tIf you do not want to use LDAP as backend, set the environmental"
        print "\tvariabale 'USERCONFIG_USES_LDAP' to 'False'."
        print "==================================================================="
        return LdapContext(editmode)

###########################################################################
# Base classes.
#
class Context(object):
    """Contains all of the information about the current authorisation
    database, plus some useful methods for modify this information.

    """
    def __init__(self):
        self._users = []
        self._groups = []
        self._shells = None
        self._setDefaultValues()

    def newUser(self,defaults=False,systemuser=False):
        """Create a new UnixUser object.

        Creates a new blank UnixUser object. The object is not part of the
        current Context. You need to add it yourself using addUser().

        Newly allocated UIDs are unique with respect to the list of UnixUser
        objects in the Context. 

        Keyword arguments:
        defaults -- Set to true if the new object should be filled in with
                    reasonable default values for the UID and username.
                    (default False)
        systemuser -- Should the new user be allocated a UID from the system
                      range of UIDs. (default is False)

        Returns a new UnixUser object.
        """
        newuserobj = self._createUser()
        if defaults:
            if systemuser:
                r = xrange(0,self.last_system_uid)
            else:
                r = xrange(self.first_uid,self.last_uid)
            for candiate in r:
                for u in self._users:
                    if u.getUID()==candiate:
                        break
                else:
                    newuserobj.setUID(candiate)
                    break

            if self.lookupUsername(u'new_user') is None:
                newuserobj.setUsername(u'new_user')
            else:
                i = 1
                while 1:
                    if self.lookupUsername(u'new_user_'+str(i)) is None:
                        newuserobj.setUsername(u'new_user_'+str(i))
                        break
                    i += 1
        return newuserobj

    def getUsers(self):
        """Get a list of all existing users.

        Returns an array of UnixUser objects.
        """
        #print "USERS:", self._users
        return self._users[:]  

    def getGroups(self):
        """Get a list of all existing groups.

        Returns an array of UnixGroup objects.
        """
        try:
            self._groups.remove("new_user")
        except ValueError:
            print "no user removed"
            pass
        return self._groups[:]

    def newGroup(self,defaults=False,systemgroup=False):
        """Create a new UnixGroup object.

        Creates a new blank UnixGroup object. The object is not part of the
        current Context. You need to add it yourself using addGroup().

        Newly allocated GIDs are unique with respect to the list of UnixGroup
        objects in the Context. 

        Keyword arguments:
        defaults -- Set to true if the new object should be filled in with
                    reasonable default values for the GID and groupname.
                    (default False)
        systemgroup  -- Set to True if the newly allocated GID should come
                        from the pool of system group IDs. (default False)

        Returns a new UnixGroup object.
        """
        newgroupobj = self._createGroup()
        if defaults:
            if systemgroup:
                r = xrange(0,self.last_system_gid)
            else:
                r = xrange(self.first_gid,self.last_gid)
            for candiate in r:
                for u in self._groups:
                    if u.getGID()==candiate:
                        break
                else:
                    newgroupobj.setGID(candiate)
                    break
            if self.lookupGroupname(u'new_group') is None:
                newgroupobj.setGroupname(u'new_group')
            else:
                i = 1
                while 1:
                    if self.lookupGroupname(u'new_user_'+str(i)) is None:
                        newgroupobj.setGroupname(u'new_user_'+str(i))
                        break
                    i += 1
        return newgroupobj

    def _createGroup(self):
        raise NotImplementedError, "Context.newGroup()"

    def addUser(self,userobj):
        """Adds the given user to the authorisation database.

        This change only takes effect after calling context.save().

        Keyword arguments:
        userobj -- The UnixUser object to add.
        """
        self._users.append(userobj)

    def addGroup(self,groupobj):
        """Adds the given group to the authorisation database.

        This change only takes effect after calling context.save().

        Keyword arguments:
        groupobj -- The UnixGroup object to add.
        """
        if groupobj not in self._groups:
            self._groups.append(groupobj)

    def removeUser(self,userobj):
        """Removes the given user object from the authorisation database.

        The user is also removed from all groups.

        This change only takes effect after calling context.save().
        """
        for g in userobj.getGroups():
            userobj.removeFromGroup(g)

        self._users.remove(userobj)

    def removeGroup(self,groupobj):
        """Removes the given group object from the authorisation database.

        All users are removed from the group.

        This change only takes effect after calling context.save().
        """
        for u in groupobj.getUsers():
            u.removeFromGroup(groupobj)

        self._groups.remove(groupobj)

    def lookupUID(self,uid):
        """Lookup a UnixUser object by its numeric user ID.

        Keyword arguments:
        uid -- User ID to lookup, integer.

        Returns the matching UnixUser object or None if it was not found.
        """
        for user in self._users:
            if user.getUID()==uid:
                return user
        return None

    def lookupUsername(self,username):
        """Lookup a UnixUser object by username.

        Keyword arguments:
        username -- Username to lookup, string.

        Returns the matching UnixUser object or None if it was not found.
        """
        for user in self._users:
            if user.getUsername()==username:
                return user
        return None

    def lookupGID(self,gid):
        """Lookup a UnixGroup object by its numeric group ID.

        Keyword arguments:
        gid -- Group ID to lookup, integer.

        Returns the matching UnixGroup object or None if it was not found.
        """
        for group in self._groups:
            if group.getGID()==gid:
                return group
        return None

    def lookupGroupname(self,groupname):
        """Lookup a UnixGroup object by groupname.

        Returns the matching UnixGroup object or None if it was not found.
        """
        for group in self._groups:
            if group.getGroupname()==groupname:
                return group
        return None

    def getUserShells(self):
        """Get the list of available login shells.

        Returns an array of strings.
        """
        if self._shells is None:
            self._shells = []
            fhandle = codecs.open('/etc/shells','r',locale.getpreferredencoding())
            for l in fhandle.readlines():
                # TODO: strangely this lets some comented lines slip through
                if len(l.strip()) > 1 and l.strip()[0] is not "#":
                    # Only show existing shells
                    if os.path.isfile(l.strip()): 
                        self._shells.append(l.strip())
            fhandle.close()
        return self._shells[:]

    def save(self):
        """Synchronises the Context with the underlying operating system.

        After a successful save, any changes to the Context will be reflected
        system wide.
        """
        raise NotImplementedError, "Context.save()"

    def createHomeDirectory(self,userobj):
        if os.path.exists(userobj.getHomeDirectory()):
            raise IOError, u"Home directory %s already exists." % userobj.getHomeDirectory()

        # Copy the skeleton directory over
        shutil.copytree(self._getSkeletonDirectory(),userobj.getHomeDirectory(),True)

        # Fix the file ownership stuff
        uid = userobj.getUID()
        gid = userobj.getPrimaryGroup().getGID()
        os.chmod(userobj.getHomeDirectory(),self.dir_mode)
        #os.system("chmod "+self.dir_mode+" "+userobj.getHomeDirectory())
        #print "Setting permissions:", userobj.getHomeDirectory(),self.dir_mode
        os.lchown(userobj.getHomeDirectory(),uid,gid)
        for root,dirs,files in os.walk(userobj.getHomeDirectory()):
            for d in dirs:
                os.lchown(os.path.join(root,d),uid,gid)
            for f in files:
                os.lchown(os.path.join(root,f),uid,gid)

    def removeHomeDirectory(self,userobj):
        if os.path.exists(userobj.getHomeDirectory()):
            shutil.rmtree(userobj.getHomeDirectory())

    def _createUser(self):
        raise NotImplementedError, "Context._createUser()"

    def _sanityCheck(self):
        userids = []
        for u in self._users:
            if isinstance(u,UnixUser)==False:
                raise TypeError,"Found an object in the list of users that is not a UnixUser object."
            uid = u.getUID()
            if uid in userids:
                raise ValueError, "User ID %i appears more than once." % uid
            userids.append(uid)
            u._sanityCheck()

        groupids = []
        for g in self._groups:
            if isinstance(g,UnixGroup)==False:
                raise TypeError,"Found an object in the list of groups that is not a UnixGroup object."
            gid = g.getGID()
            if gid in groupids:
                raise ValueError, "Group ID %i appears more than once." % gid
            groupids.append(gid)    
            g._sanityCheck()

    def _getSkeletonDirectory(self):
        return self.skel

    def _readAdduserConf(self):
        """ Fill a dictionary with the values from /etc/adduser.conf
            which then can be used as default values, if the file exists
            at least. 
            Attention: We're not validating!"""
        self.defaults = {}
        self.adduserconf = '/etc/adduser.conf'
        if not os.path.isfile(self.adduserconf):
            return
        fhandle = codecs.open(self.adduserconf,'r',locale.getpreferredencoding())
        for line in fhandle.readlines():
            line = line.strip()
            parts = line.split("=")
            if len(parts) == 2:
                self.defaults[str(parts[0].strip())] = parts[1].strip()

    def _setDefaultValues(self):
        """ Set a lot of default values for UIDs and GIDs, try to use the values
            from /etc/adduser.conf."""
        self._readAdduserConf()

        try:
            self.skel = self.defaults["SKEL"]
        except KeyError:
            self.skel = '/etc/skel'

        # IDs for new users and groups.
        try:
            self.first_uid = int(self.defaults['FIRST_UID'])
        except (KeyError,ValueError):
            self.first_uid = 1000

        try:
            self.last_uid = int(self.defaults["LAST_UID"])
        except (KeyError,ValueError):
            self.last_uid = 29999

        try:
            self.first_gid = int(self.defaults["FIRST_GID"])
        except (KeyError,ValueError):
            self.first_gid = 1000

        try:
            self.last_gid = int(self.defaults["LAST_GID"])
        except (KeyError,ValueError):
            self.last_gid = 65534

        # Which IDs are system user and system groups?
        try:
            self.first_system_uid = int(self.defaults["FIRST_SYSTEM_UID"])
        except (KeyError,ValueError):
            self.first_system_uid = 500

        try:
            self.last_system_uid = int(self.defaults["LAST_SYSTEM_UID"])
        except (KeyError,ValueError):
            self.last_system_uid = 65534

        try:
            self.first_system_gid = int(self.defaults["FIRST_SYSTEM_GID"])
        except (KeyError,ValueError):
            self.first_system_gid = 500

        try:
            self.last_system_gid = int(self.defaults["LAST_SYSTEM_GID"])
        except (KeyError,ValueError):
            self.last_system_gid = 65534

        # More defaults which might make sense.
        try:
            self.dir_mode = int(self.defaults["DIR_MODE"],8)
        except (KeyError,ValueError):
            self.dir_mode = int("0755",8)
            print "Didn't read default DIR_MODE"

        try:
            self.dhome = self.defaults["DHOME"]
        except KeyError:
            self.dhome = "/home"

        try:
            self.dshell = self.defaults["DSHELL"]
        except KeyError:
            # Will be set in showNewUser()
            self.dshell = None


###########################################################################
class UnixAccount(object):
    """ Common interface for users and groups """
    def getID(self):
        """ Returns the numerical ID of the object ( e.g. UID, GID) """
        pass
    
    def getSystemName(self):
        """ Returns the name of the object as referred to in the system
            ( e.g. username, group name )
        """
        pass
    
    def isSystemAccount(self):
        """ See if this account is a system account.

            Returns True or False.
        """
        pass

###########################################################################
class UnixUser(UnixAccount):
    def __init__(self,context):
        self._context = context
        self._uid = None
        self._username = None

        # UnixGroup object.
        self._primarygroup = None

        # List of UnixGroup objects.
        self._groups = []

        self._gecos = None
        self._homedirectory = None
        self._loginshell = None

        self._islocked = False

        self._encpass = ""

        # FIXME : This should actually be days since epoch or something like this
        self._passlastchange = 0 
        self._passminimumagebeforechange = 0
        self._passmaximumage = None
        self._passexpirewarn = 7
        self._passexpiredisabledays = None
        self._disableddays = None

    def polish(self):
        primary_group = self._context.lookupGID(self._gid)
        if primary_group is None:
            # The GID didn't match an existing group. Quickly make a new group.
            new_group = self._context.newGroup()
            new_group.setGID(self._gid)

            new_group_name = u"group%i" % self._gid
            i = 0
            while self._context.lookupGroupname(new_group_name) is not None:
                i += 1
                new_group_name = u"group%i_%i" % (self._gid,i)
            new_group.setGroupname(new_group_name)

            self._context.addGroup(new_group)
            primary_group = new_group

        self.setPrimaryGroup(primary_group)
        for group in self._context._groups:
            if group.contains(self):
                self._groups.append(group)

    def getUID(self):
        """Get the unix user ID.

        Returns the integer.
        """
        return self._uid

    def setUID(self,uid):
        """Set the unix user ID.

        Keyword arguments:
        uid -- Integer user id.
        """
        uid = int(uid)
        if uid<0:
            raise ValueError, "User ID (%i) is a negative number." % uid
        self._uid = uid

    def isSystemUser(self):
        """See if this user is a system user.

        Returns True or False.
        """
        return not (self._context.first_uid <= self._uid < self._context.last_uid)

    def getUsername(self): return self._username

    def setUsername(self,username): self._username = username

    def getPrimaryGroup(self):
        """Get the primary group for this user.

        Returns a UnixGroup object.
        """
        return self._primarygroup

    def setPrimaryGroup(self,groupobj):
        """Set the primary group for this user.

        If the given group is not part of this user's list of groups, then
        it will be added.

        Keyword arguments:
        groupobj -- The group to set as the primary group.
        """
        self.addToGroup(groupobj)
        self._primarygroup = groupobj

    def getGroups(self):
        """Get the list of groups that this user belongs to.

        The user's primary group is also included in the returned list.

        Returns a list of UnixGroup objects. Modify the list does not affect
        this UnixUser object.
        """
        return self._groups[:]

    def addToGroup(self,groupobj):
        """Add this user to the given group.

        Keyword arguments:
        groupobj -- UnixGroup object.
        """
        groupobj._addUser(self)
        if groupobj not in self._groups:
            self._groups.append(groupobj)

    def removeFromGroup(self,groupobj):
        """Remove this user from the given group.

        If group is current this user's primary group, then

        Keyword arguments:
        groupobj -- UnixGroup object.
        """
        groupobj._removeUser(self)
        try:
            self._groups.remove(groupobj)
        except ValueError:
            pass
        if self._primarygroup is groupobj:
            if len(self._groups)==0:
                self._primarygroup = None
            else:
                self._primarygroup = self._groups[0]

    def setPassword(self,password):
        # Make some salt.
        space = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQSRTUVWXYZ0123456789./'
        salt = ""
        for x in range(8):
            salt += space[random.randint(0,len(space)-1)]
        self._encpass = crypt.crypt(password,'$1$'+salt+'$')

    def isLocked(self): return self._islocked
    def setLocked(self,locked): self._islocked = locked

    def getRealName(self): 
        if not self._gecos:
            return ""
        try:
            return self._gecos.split(",")[0]
        except AttributeError:
            return self._gecos

    def setRealName(self,realname): self._gecos = realname
    def getHomeDirectory(self): return self._homedirectory
    def setHomeDirectory(self,homedirectory): self._homedirectory = homedirectory
    def getLoginShell(self): return self._loginshell
    def setLoginShell(self,loginshell): self._loginshell = loginshell

    # 'None' means that there is no maximum password age.
    def getMaximumPasswordAge(self): return self._passmaximumage
    def setMaximumPasswordAge(self,days): self._passmaximumage = days

    def getMinimumPasswordAgeBeforeChange(self): return self._passminimumagebeforechange
    def setMinimumPasswordAgeBeforeChange(self,days): self._passminimumagebeforechange = days
    def getPasswordDisableAfterExpire(self): return self._passexpiredisabledays
    def setPasswordDisableAfterExpire(self,days): self._passexpiredisabledays = days
    def getPasswordExpireWarning(self): return self._passexpirewarn
    def setPasswordExpireWarning(self,days): self._passexpirewarn = days
    def getLastPasswordChange(self): return self._passlastchange
    def getExpirationDate(self): return self._disableddays
    def setExpirationDate(self,unixdate): self._disableddays = unixdate

    def __str__(self):
        return "%s(%i)" % (self._username,self._uid)

    def _sanityCheck(self):
        if self._primarygroup is None:
            raise ValueError,"Userobj has no primary group!"
        if self._uid is None:
            raise ValueError,"Userobj has no UID!"

    # Common interface for users and groups ###############################
    def getID(self):
        """ Returns the numerical ID of the object ( e.g. UID, GID) """
        return self.getUID()
    
    def getSystemName(self):
        """ Returns the name of the object as referred to in the system
            ( e.g. username, group name )
        """
        return self.getUsername()
    
    def isSystemAccount(self):
        """ See if this account is a system account.

            Returns True or False.
        """
        return self.isSystemUser()

###########################################################################
class UnixGroup(UnixAccount):
    def __init__(self,context):
        self._context = context

        # List of UnixUser objects.
        self._members = []

        self._gid = None
        self._groupname = None

    def contains(self,userobj):
        """Check if a the given user is a member of this group.

        Returns True or False.
        """
        return userobj in self._members

    def polish(self): pass
    def isSystemGroup(self):
        """Check if this group is a system group.

        Returns True or False.
        """
        return not (self._context.first_gid <= self._gid < self._context.last_gid)
        #return not (500 <= self._gid < 65534)

    def getGID(self):
        """Get the unix group ID.

        Returns the integer group id.
        """
        return self._gid

    def setGID(self,gid):
        """Set the unix group ID.

        Keyword arguments:
        gid -- new group id, integer.
        """
        self._gid = gid

    def getGroupname(self): return self._groupname
    def setGroupname(self,groupname): self._groupname = groupname
    def getUsers(self): return self._members[:]
    def _addUser(self,userobj):
        if not self.contains(userobj):
            self._members.append(userobj)

    def _removeUser(self,userobj):
        try:
            self._members.remove(userobj)
        except ValueError:
            pass

    def __str__(self):
        # FIXME encoding
        return str(self._groupname) + " (" + str(self._gid) + ") " + str([str(u) for u in self._members])

    def _sanityCheck(self):
        pass

    # Common interface for users and groups ###############################
    def getID(self):
        """ Returns the numerical ID of the object ( e.g. GID) """
        return self.getGID()
    
    def getSystemName(self):
        """ Returns the name of the object as referred to in the system
            ( e.g. group name )
        """
        return self.getGroupname()
    
    def isSystemAccount(self):
        """ See if this group is a system group.

            Returns True or False.
        """
        return self.isSystemGroup()


###########################################################################
class PwdContext(Context):
    #def __init__(self,editmode,passwordfile="etc-passwd",groupfile='etc-group',shadowfile="etc-shadow"):
    def __init__(self,editmode,passwordfile="/etc/passwd",groupfile='/etc/group',shadowfile="/etc/shadow"):
        Context.__init__(self)
        self.__editmode = editmode
        self.__passwordfile = passwordfile
        self.__groupfile = groupfile
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
class LdapContext(Context):

    def __init__(self,editmode,server="localhost",admin_dn="",admin_pass=""):
        """ Connect to the LDAP server and invoke further actions. 
        """
        Context.__init__(self)
        # admin_dn is DistinguishedName? (or dn, for short)
        self.server = server
        self.baseDN = "dc=vizZzion,dc=net"

        self.url = "ldap://"+self.server

        self.ldapserver = ldap.initialize(self.url)
        self.ldapserver.protocol_version = ldap.VERSION3

        self.editmode = editmode
        if not self.editmode:
            self.ldapserver.simple_bind("admin",admin_pass)
        print "Connected to ", self.url

        self._users = self._getUsers()

    def _getUsers(self):
        """ Retrieve a list of users from the LDAP server.
        """
        _users = []
        print "LdapContext._getUsers"
        searchScope = ldap.SCOPE_SUBTREE
        retrieveAttributes = None 
        searchFilter = "cn=*"
        try:
            ldap_result_id = self.ldapserver.search(self.baseDN, searchScope, searchFilter, retrieveAttributes)
            result_set = []
            while 1:
                result_type, result_data = self.ldapserver.result(ldap_result_id, 0)
                if (result_data == []):
                    break
                else:
                    if result_type == ldap.RES_SEARCH_ENTRY:
                        #print result_data[0][1]
                        #print " --------------------- "
                        result_set.append(result_data[0][1])
            #print result_set
        except ldap.LDAPError, e:
            print "ERROR: ",e

        if len(result_set) == 0:
            print "No Results."
            return 
        count = 0
        """
        for entry in result_set:
            for d in entry.keys():
                print d, "::", entry[d]
            print "======== Next User =============="
        """
        # Walk through result_set and create users.
        for entry in result_set:
            try:
                name = entry['cn'][0]
                login = entry['uid'][0]
                loginshell = entry['loginShell'][0]
                homedirectory = entry['homeDirectory'][0]
                uid = entry['uidNumber'][0]
                gid = entry['gidNumber'][0]
                count = count + 1
                #print "\n%d. User: %s\n\tName: %s\n\tShell: %s\n\tHomeDir: %s\n\tUID: %s\n\tGID: %s\n" %\
                #       (count, login, name, loginshell, homedirectory, uid, gid)
                # Create a new userobject
                new_user = self._createUser()
                new_user.setHomeDirectory(homedirectory)
                new_user.setUID(uid)
                new_user.setRealName(name)
                new_user.setLoginShell(loginshell)
                new_user.setUsername(login)
                _users.append(new_user)
                print "Number of Users:", len(self._users)

            except KeyError, e:
                # Debugging output...
                print "ERR:: ",e
                print 'err:: ',entry
        return _users

    def _createUser(self):
        return LdapUser(self)

    def _createGroup(self):
        return LdapGroup(self)

    def save(self):
        print "LdapContext.save() does nothing yet."

###########################################################################
class LdapUser(UnixUser):

    def __str__(self):
        return "LdapUser: %s(%i)" % (self._username,self._uid)


###########################################################################
class LdapGroup(UnixGroup):

    def __str__(self):
        return "LdapGroup: %s(%i)" % (self._username,self._uid)


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

###########################################################################
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

###########################################################################

if __name__=='__main__':
    print "Testing"
    context = getContext(True)

    print "Stopping here..."
    #import sys
    #sys.exit(0) ## Remove.
    #print "Users:"
    #for user in context.getUsers():
    for user in context._users:
        print "--------------------------------------------------"
        print "UID:",user.getUID()
        print "Is system user:",user.isSystemUser()
        print "Username:",user.getUsername()
        print "Primary Group:",str(user.getPrimaryGroup())
        print "Groups:",[str(u) for u in user.getGroups()]
        print "Is locked:",user.isLocked()
        print "Real name:",user.getRealName()
        print "Home Dir:",user.getHomeDirectory()
        print "Maximum password age:",user.getMaximumPasswordAge()
        print "Minimum password age before change:",user.getMinimumPasswordAgeBeforeChange()
        print "Expire warning:",user.getPasswordExpireWarning()
        print "Disable after Expire:",user.getPasswordDisableAfterExpire()
        #print user._getPasswdEntry()

    print "Groups"
    for group in context.getGroups():
        print str(group)
        #print group._getGroupFileEntry()

    print "Saving"    
    context.save()
