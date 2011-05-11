#!/usr/bin/python
# -*- coding: utf-8 -*-
###########################################################################
#    Copyright (C) 2004-2006 by Simon Edwards
#    <simon@simonzone.com>
#    Copyright (C) 2011 by Romain Perier
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

    def getDisplayName(self):
        """ Returns the name of the object as it should be displayed on
            the screen.  Real name with fallback to username.
        """
        name = self.getRealName()
        if name:
            return name
        else:
            return self.getSystemName()

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

if __name__=='__main__':
    print "Testing"
    print help(PwdContext)
    context = getContext(False)
    os.exit(0)

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
