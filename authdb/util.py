# -*- coding: utf-8 -*-

#############################################################################
##
## Copyright 2004-2006 Simon Edwards
## Copyright 2011 Romain Perier
## Author: Romain Perier <romain.perier@gmail.com>
##         Simon Edwards <simon@simonzone.com>
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

from pwd import *
from ldap import *

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
