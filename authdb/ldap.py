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

ldaperror = ""
try:
    import ldap 
except ImportError:
    ldaperror = "The LDAP Python Module is not installed, but needed to use LDAP. Install it."


from context import *

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
