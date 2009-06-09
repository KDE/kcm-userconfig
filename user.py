#!/usr/bin/python
# -*- coding: utf-8 -*-
###########################################################################
# user.py - configuration for users for userconfig                        #
# ------------------------------                                          #
# begin     : Wed Apr 30 2003                                             #
# copyright : (C) 2003-2006 by Simon Edwards,                             #
#                 2008-2009 by Yuriy Kozlov, Jonathan Thomas, Ralph Janke #
# email     : simon@simonzone.com,                                        #
#             yuriy-kozlov@kubuntu.org                                    #
#                                                                         #
###########################################################################
#                                                                         #
#   This program is free software; you can redistribute it and/or modify  #
#   it under the terms of the GNU General Public License as published by  #
#   the Free Software Foundation; either version 2 of the License, or     #
#   (at your option) any later version.                                   #
#                                                                         #
###########################################################################

import os.path
import shutil

# Qt imports
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4 import uic

# KDE imports
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.kio import *

import locale

# userconfig imports
#from util.groups import PrivilegeNames
from models import GroupListModel, PrivilegeListProxyModel,\
                   SimpleGroupListProxyModel

###########################################################################
def SptimeToQDate(sptime):
    t = QDateTime()
    t.setTime_t(0)
    return t.addDays(sptime).date()

###########################################################################
def QDateToSptime(qdate):
    x = QDateTime()
    x.setTime_t(0)
    return x.daysTo(QDateTime(qdate))

class UserEditDialog(KPageDialog):
    def __init__(self,parent,admincontext):
        KPageDialog.__init__( self, parent )
        self.setFaceType(KPageDialog.Tabbed)
        self.setCaption(i18n("User Account"))
        self.setModal(True)
        
        self.details_tab = uic.loadUi('ui/userproperties-details.ui')
        self.addPage(self.details_tab, i18n("Details"))
        self.privgroups_tab = uic.loadUi('ui/userproperties-privgroups.ui')
        self.addPage(self.privgroups_tab, i18n("Privileges and Groups"))
        self.pwsec_tab = uic.loadUi('ui/userproperties-pwsec.ui')
        self.addPage(self.pwsec_tab, i18n("Password/Security"))

        self.admincontext = admincontext
        self.userobj = None
        
        self.updatingGUI = True
        
        self.groups_model = GroupListModel(None,
                                           self.admincontext.getGroups(),
                                           self.userobj)

        #######################################################################
        # Set up the user details tab
        
        self.details_tab.enabledradio.setIcon(KIcon("user-identity"))
        self.details_tab.disabledradio.setIcon(KIcon("object-locked"))
        
        self.details_tab.enabledradiogroup = QButtonGroup()
        self.details_tab.enabledradiogroup.addButton(
                                        self.details_tab.enabledradio, 0)
        self.details_tab.enabledradiogroup.addButton(
                                        self.details_tab.disabledradio, 1)

        self.details_tab.loginnameedit.setValidator(
                        LoginNameValidator(self.details_tab.loginnameedit))

        self.connect(self.details_tab.loginnameedit,
                     SIGNAL("textChanged(const QString &)"),
                     self.slotLoginChanged)

        self.details_tab.realnameedit.setValidator(
                        RealUserNameValidator(self.details_tab.realnameedit))

        self.details_tab.uidedit.setValidator(
                        QIntValidator(0, 65535, self.details_tab.uidedit))

        self.details_tab.primarygroupedit.setValidator(
                        LoginNameValidator(self.details_tab.primarygroupedit))
        self.details_tab.primarygroupedit.setInsertPolicy(
                        QComboBox.NoInsert)
        self.simple_groups_model = SimpleGroupListProxyModel(None)
        self.simple_groups_model.setSourceModel(self.groups_model)
        self.details_tab.primarygroupedit.setModel(self.simple_groups_model)
        self.connect(self.details_tab.primarygroupedit,
                     SIGNAL("editTextChanged(const QString&)"),
                     self.slotPrimaryGroupChanged)
        
        self.connect(self.details_tab.homediredit,
                     SIGNAL("textChanged(const QString &)"),
                     self.slotHomeDirChanged)
        self.connect(self.details_tab.homedirbutton,
                     SIGNAL("clicked()"),
                     self.slotBrowseHomeDirClicked)

        for shell in self.admincontext.getUserShells():
            self.details_tab.shelledit.addItem(shell)

        #######################################################################
        # Set up the privileges and groups tab
        self.privgroups_tab.groupslistview.setModel(self.groups_model)
        
        self.privileges_model = PrivilegeListProxyModel(None)
        self.privileges_model.setSourceModel(self.groups_model)
        self.privgroups_tab.privilegeslistview.setModel(self.privileges_model)

        #######################################################################
        # Set up the password/security tab
        
        #FIXME Doesn't work
        #self.up.passwordLabel.setPixmap(UserIcon("hi32-password"))
        
        self.pwsec_tab.validradiogroup = QButtonGroup()
        self.pwsec_tab.validradiogroup.addButton(
                            self.pwsec_tab.validalwaysradio, 0)
        self.pwsec_tab.validradiogroup.addButton(
                            self.pwsec_tab.expireradio, 1)
        self.connect(self.pwsec_tab.expireradio,
                     SIGNAL("toggled(bool)"),
                     self.slotValidUntilToggled)

        # Password Aging & Expiration.

        # [*] Require new password after: [_____5 days]
        self.connect(self.pwsec_tab.forcepasswordchangecheckbox,
                     SIGNAL("toggled(bool)"),
                     self.slotForcePasswordChangeToggled)

        self.pwsec_tab.warningedit.setSpecialValueText(i18n("Never"))

        self.pwsec_tab.disableexpireedit.setSpecialValueText(i18n("Never"))

        self.connect(self.pwsec_tab.enforcepasswordminagecheckbox,
                     SIGNAL("toggled(bool)"),
                     self.slotEnforePasswordAgeToggled)

        self.homedirdialog = KDirSelectDialog(KUrl.fromPath("/"),True,self)
        self.createhomedirectorydialog = OverwriteHomeDirectoryDialog(None)
        
        # Data changed signals
        # Details tab
        self.connect(self.details_tab.enabledradio,
                     SIGNAL("toggled(bool)"),
                     self.slotDataChanged)
        self.connect(self.details_tab.loginnameedit,
                     SIGNAL("textEdited(const QString&)"),
                     self.slotDataChanged)
        self.connect(self.details_tab.realnameedit,
                     SIGNAL("textEdited(const QString&)"),
                     self.slotDataChanged)
        self.connect(self.details_tab.primarygroupedit,
                     SIGNAL("editTextChanged(const QString&)"),
                     self.slotDataChanged)
        self.connect(self.details_tab.homediredit,
                     SIGNAL("textEdited(const QString&)"),
                     self.slotDataChanged)
        self.connect(self.details_tab.shelledit,
                     SIGNAL("editTextChanged(const QString&)"),
                     self.slotDataChanged)
        # Groups tab
        self.connect(self.groups_model,
                     SIGNAL("modelReset()"),
                     self.slotDataChanged)
        # Password/security tab
        self.connect(self.pwsec_tab.passwordedit,
                     SIGNAL("textEdited(const QString&)"),
                     self.slotDataChanged)
        self.connect(self.pwsec_tab.expireradio,
                     SIGNAL("toggled(bool)"),
                     self.slotDataChanged)
        self.connect(self.pwsec_tab.expiredate,
                     SIGNAL("changed(const QDate&)"),
                     self.slotDataChanged)
        self.connect(self.pwsec_tab.forcepasswordchangecheckbox,
                     SIGNAL("toggled(bool)"),
                     self.slotDataChanged)
        self.connect(self.pwsec_tab.maximumpasswordedit,
                     SIGNAL("valueChanged(int)"),
                     self.slotDataChanged)
        self.connect(self.pwsec_tab.warningedit,
                     SIGNAL("valueChanged(int)"),
                     self.slotDataChanged)
        self.connect(self.pwsec_tab.disableexpireedit,
                     SIGNAL("valueChanged(int)"),
                     self.slotDataChanged)
        self.connect(self.pwsec_tab.enforcepasswordminagecheckbox,
                     SIGNAL("toggled(bool)"),
                     self.slotDataChanged)
        self.connect(self.pwsec_tab.minimumpasswordedit,
                     SIGNAL("valueChanged(int)"),
                     self.slotDataChanged)
        
        self.updatingGUI = False
        
    
    ########################################################################
    def showEditUser(self, userid):
        """ Sets up the dialog to modify an existing user.
            Returns the UID of the user if successful, None otherwise.
        """
        self.updatingGUI = True
        self.newusermode = False
        self.userobj = self.admincontext.lookupUID(userid)
        self.setCaption(i18n("Modifying User Account %1")\
                            .arg(self.userobj.getUsername()))
        # Set up buttons
        self.setButtons(KDialog.ButtonCode(KDialog.Cancel | KDialog.Ok |
                                           KDialog.Apply))
        self.connect(self, SIGNAL("applyClicked()"), self.applyChanges)
        
        self.pwsec_tab.passwordedit.clear()
        
        # Save the groups so they can be restored, and for isChanged()
        self.originalgroups = [g for g in self.userobj.getGroups()
                                     if g is not self.userobj.getPrimaryGroup()]
        self.originalprimarygroup = self.userobj.getPrimaryGroup()
        
        # FIXME we should repopulate the groups
        # privileges list when the primary group is changed in the other tab --
        # that is, on the change slot of the primary group drop down.
        self.groups_model.setUser(self.userobj)
        
        # Puts most of the user data into the GUI
        self.__syncGUI()
        
        self.details_tab.uidedit.setReadOnly(True)
        
        self.updatingGUI = False
        self.homedirectoryislinked = False
        self.primarygroupislinked = False
        
        if self.exec_() == QDialog.Accepted:
            result = self.applyChanges()
            self.pwsec_tab.passwordedit.clear()
            if result:
                return self.userobj.getUID()
            else:
                return None
        else: # Dialog rejected
            # Revert secondary groups, since those are being stored in the user
            #  by the model
            currentgroups = [g for g in self.userobj.getGroups()
                                   if g not in (self.userobj.getPrimaryGroup(),
                                                self.originalprimarygroup)]
            addedgroups = [g for g in currentgroups
                               if g not in self.originalgroups]
            removedgroups = [g for g in self.originalgroups
                               if g not in currentgroups]
            for group in removedgroups:
                self.userobj.addToGroup(group)
            for group in addedgroups:
                self.userobj.removeFromGroup(group)
            
            # Revert the primary group
            self.userobj.setPrimaryGroup(self.originalprimarygroup)
            
            self.pwsec_tab.passwordedit.clear()
            return None

    ########################################################################
    def showNewUser(self):
        """ Sets up the dialog to create a new user.
            Returns the UID of the new user if successful, None otherwise.
        """
        self.updatingGUI = True
        self.newusermode = True
        self.userobj = self.admincontext.newUser(True)
        self.setCaption(i18n("New User Account"))
        # Set up buttons
        self.setButtons(KDialog.ButtonCode(KDialog.Cancel | KDialog.Ok))

        self.newgroup = self.admincontext.newGroup(True)
        self.newgroup.setGroupname(self.__fudgeNewGroupName(
                                            self.userobj.getUsername()))
        self.userobj.setPrimaryGroup(self.newgroup)

        # Add the new user to a default set of groups
        # TODO: move this list somewhere more general?
        self.selectedgroups = [ u'dialout',u'cdrom',u'floppy',u'audio',u'video',
                                u'plugdev',u'lpadmin',u'scanner']
        for groupname in self.selectedgroups:
            groupobj = self.admincontext.lookupGroupname(groupname)
            if groupobj: self.userobj.addToGroup(groupobj)
        
        # FIXME consider adding a drop down that will select the appropriate
        # profile Limited User, Advanced User or Administrator (and see if
        # there is a config file where these profiles can be read).
        # We are repopulating because if the user to edit changes, we need to
        # hide the user's secondary group.
        self.groups_model.setUser(self.userobj)
        
        homedir = self.__fudgeNewHomeDirectory(self.userobj.getUsername())
        self.userobj.setHomeDirectory(homedir)

        shells = self.admincontext.getUserShells()
        dshell = self.admincontext.dshell
        if dshell and (dshell in shells):
            self.userobj.setLoginShell(dshell)
        elif '/bin/bash' in shells:
            self.userobj.setLoginShell('/bin/bash')
        elif '/bin/sh' in shells:
            self.userobj.setLoginShell('/bin/sh')
        elif len(shells) != 0:
            self.userobj.setLoginShell(shells[0])

        # Puts most of the user data into the GUI
        self.__syncGUI()

        self.details_tab.uidedit.setReadOnly(False)
        self.pwsec_tab.passwordedit.clear()
        
        self.updatingGUI = False
        self.homedirectoryislinked = True
        self.primarygroupislinked = True
        
        if self.exec_() == QDialog.Accepted:
            result = self.applyChanges()
            self.pwsec_tab.passwordedit.clear()
            if result:
                return self.userobj.getUID()
            else:
                return None
        else: # Dialog rejected
            self.pwsec_tab.passwordedit.clear()
            return None

    ########################################################################
    def sanityCheck(self):
        """ Do some sanity checks.
            Returns True if data is ok or has been fixed up, otherwise pops up
            a message and returns False
        """
        # Check that the username doesn't clash
        # TODO: do this in the UI instead of canceling the operation
        newusername = unicode(self.details_tab.loginnameedit.text())
        existinguser = self.admincontext.lookupUsername(newusername)
        if existinguser is not None and existinguser is not self.userobj:
            KMessageBox.sorry(self, i18n("Sorry, you must choose a different " +
                                         "user name.\n" +
                                         "'%1' is already being used.")\
                                         .arg(newusername))
            return False
        
        # Check that the UID doesn't clash (can't change UID of existing user)
        # TODO: do this in the UI instead of canceling the operation
        if self.newusermode:
            newuid = int(unicode(self.details_tab.uidedit.text()))
            originaluid = self.userobj.getUID()
            if self.admincontext.lookupUID(newuid) is not None:
                rc = KMessageBox.questionYesNo(self,
                        i18n("Sorry, the UID %1 is already in use. Should %2" +
                             " be used instead?").arg(newuid).arg(originaluid),
                        i18n("User ID in use"))
                if rc == KMessageBox.Yes:
                    self.details_tab.uidedit.setValue(unicode(originaluid))
                else:
                    return False
        
        return True

    ########################################################################
    def applyChanges(self):
        if not self.newusermode and not self.isChanged():
            return False
        
        if not self.sanityCheck():
            return False
        
        # Put in most of the data
        self.__updateObjectFromGUI(self.userobj)

        if self.newusermode:
            # Decide what to do about the home directory
            makehomedir = True
            deleteoldhomedir = False
            if os.path.exists(self.userobj.getHomeDirectory()):
                rc = self.createhomedirectorydialog.do(self.userobj)
                if rc == OverwriteHomeDirectoryDialog.CANCEL:
                    return False
                if rc == OverwriteHomeDirectoryDialog.OK_KEEP:
                    makehomedir = False
                elif rc == OverwriteHomeDirectoryDialog.OK_REPLACE:
                    deleteoldhomedir = True

            # Add the user to the admin context.  Before this the userobj
            #  exists on its own.
            self.admincontext.addUser(self.userobj)

            # Secondary groups are updated within the model, nothing to do here

            # Set the password.
            if self.pwsec_tab.passwordedit.text() != "":
                self.userobj.setPassword(str(self.pwsec_tab.passwordedit.text()))

            # Enable/Disable the account
            self.userobj.setLocked(
                self.details_tab.enabledradiogroup.checkedId() != 0)
            
            # Save everything
            self.admincontext.save()

            # Create the home directory if needed
            if deleteoldhomedir:
                if os.path.exists(self.userobj.getHomeDirectory()):
                    shutil.rmtree(self.userobj.getHomeDirectory())
            if makehomedir:
                self.admincontext.createHomeDirectory(self.userobj)
        
        # The rest applies to both new users and existing users
        
        # Set the password.
        # TODO: password should need to be typed twice
        if self.pwsec_tab.passwordedit.text() != "":
            self.userobj.setPassword(str(self.pwsec_tab.passwordedit.text()))
            
        # Secondary groups are updated within the model, nothing to do here
        #  if dialog accepted, need to revert if rejected.

        # __updateObjectFromGUI tries to set the primary group, but won't
        #  set it if the group doesn't exist yet
        # TODO: for an existing user, ask for confirmation
        if self.admincontext.lookupGroupname(self.primarygroupname) is None:
            # Create a new group
            newgroup = self.admincontext.newGroup(True)
            newgroup.setGroupname(self.primarygroupname)
            self.admincontext.addGroup(newgroup)
            origprimarygroup = self.userobj.getPrimaryGroup()
            self.userobj.setPrimaryGroup(newgroup)
            self.userobj.removeFromGroup(origprimarygroup)
            # For Apply button, make sure views get updated
            self.groups_model.setItems(self.admincontext.getGroups())

        # Enable/Disable the account
        self.userobj.setLocked(
            self.details_tab.enabledradiogroup.checkedId() != 0)
        
        # Save everything
        self.admincontext.save()
        
        # For Apply button
        if not self.newusermode:
            # Save the groups so they can be restored, and for isChanged()
            self.originalgroups = [g for g in self.userobj.getGroups()
                                     if g is not self.userobj.getPrimaryGroup()]
            self.originalprimarygroup = self.userobj.getPrimaryGroup()
        
        self.slotDataChanged()
        
        return True
    
    ########################################################################
    def slotLoginChanged(self, text):
        newtext = unicode(text)
        if not self.updatingGUI:
            if self.newusermode:
                self.updatingGUI = True
                if self.primarygroupislinked:
                    newprimarygroupname = self.__fudgeNewGroupName(newtext)
                    self.details_tab.primarygroupedit.setEditText(
                            newprimarygroupname)
                if self.homedirectoryislinked:
                    homedir = self.__fudgeNewHomeDirectory(newtext)
                    self.details_tab.homediredit.setText(homedir)
                self.updatingGUI = False
    
    ########################################################################
    def slotPrimaryGroupChanged(self, text):
        newtext = unicode(text)
        
        if not self.updatingGUI:
            self.updatingGUI = True
            self.primarygroupislinked = False
            
            if not newtext:
                self.__selectPrimaryGroup()
            else:
                groupobj = self.admincontext.lookupGroupname(text)
                origprimarygroup = self.userobj.getPrimaryGroup()
                if groupobj is not None:
                    if groupobj is origprimarygroup:
                        self.__selectPrimaryGroup()
                    else:
                        self.userobj.setPrimaryGroup(groupobj)
                        self.userobj.removeFromGroup(origprimarygroup)
                else:
                    # FIXME: Can't remove the group here because unixauthdb
                    #   will asign a random one
                    pass
            
            self.updatingGUI = False

    ########################################################################
    def __selectPrimaryGroup(self):
        idx = self.details_tab.primarygroupedit.findText(
                            self.userobj.getPrimaryGroup().getGroupname())
        self.details_tab.primarygroupedit.setCurrentIndex(idx)

    ########################################################################
    def slotHomeDirChanged(self, newdir):
        if not self.updatingGUI:
            self.homedirectoryislinked = False
        
    ########################################################################
    def __syncGUI(self):
        if self.userobj.isLocked():
            self.details_tab.enabledradiogroup.button(1).setChecked(True)
        else:
            self.details_tab.enabledradiogroup.button(0).setChecked(True)

        self.details_tab.loginnameedit.setText(self.userobj.getUsername())
        self.details_tab.realnameedit.setText(self.userobj.getRealName())
        self.details_tab.uidedit.setText(unicode(self.userobj.getUID()))
        self.details_tab.homediredit.setText(self.userobj.getHomeDirectory())
        self.details_tab.shelledit.setEditText(self.userobj.getLoginShell())

        # Primary Group
        if self.newusermode:
            # New user mode
            newprimarygroupname = \
                self.__fudgeNewGroupName(unicode(self.userobj.getUsername()))
            self.details_tab.primarygroupedit.setEditText(newprimarygroupname)
        else:
            # Existing user mode
            primarygroupname = self.userobj.getPrimaryGroup().getGroupname()
            self.__selectPrimaryGroup()

        # If ShadowExpire is turn off then we change the radio box.
        if self.userobj.getExpirationDate() is None:
            self.pwsec_tab.validradiogroup.button(0).setChecked(True)
            self.pwsec_tab.expiredate.setDisabled(True)
            self.pwsec_tab.expiredate.setDate(SptimeToQDate(99999L))
        else:
            self.pwsec_tab.validradiogroup.button(1).setChecked(True)
            self.pwsec_tab.expiredate.setDisabled(False)
            self.pwsec_tab.expiredate.setDate(
                            SptimeToQDate(self.userobj.getExpirationDate()))

        if self.userobj.getMaximumPasswordAge() is None:
            # Password aging is turn off
            self.pwsec_tab.forcepasswordchangecheckbox.setChecked(False)
            d = True
        else:
            # Password aging is turn on
            self.pwsec_tab.forcepasswordchangecheckbox.setChecked(True)
            d = False
        self.pwsec_tab.warningedit.setDisabled(d)
        self.pwsec_tab.maximumpasswordedit.setDisabled(d)
        self.pwsec_tab.disableexpireedit.setDisabled(d)

        if self.userobj.getPasswordExpireWarning() is None:
            self.pwsec_tab.warningedit.setValue(0)
        else:
            self.pwsec_tab.warningedit.setValue(self.userobj.getPasswordExpireWarning())

        if self.userobj.getMaximumPasswordAge() is None:
            self.pwsec_tab.maximumpasswordedit.setValue(30)
        else:
            self.pwsec_tab.maximumpasswordedit.setValue(
                    self.userobj.getMaximumPasswordAge())

        if self.userobj.getPasswordDisableAfterExpire() is None:
            self.pwsec_tab.disableexpireedit.setValue(0)
        else:
            self.pwsec_tab.disableexpireedit.setValue(
                    self.userobj.getPasswordDisableAfterExpire())

        minage = self.userobj.getMinimumPasswordAgeBeforeChange()
        self.pwsec_tab.enforcepasswordminagecheckbox.setChecked(minage > 0)
        self.pwsec_tab.minimumpasswordedit.setDisabled(minage <= 0)
        if minage <= 0:
            minage = 1
        self.pwsec_tab.minimumpasswordedit.setValue(minage)

        if self.userobj.getLastPasswordChange() in (None, 0):
            self.pwsec_tab.lastchangelabel.setText('-');
        else:
            self.pwsec_tab.lastchangelabel.setText(
                KGlobal.locale().formatDate(SptimeToQDate(
                                  int(self.userobj.getLastPasswordChange()))))
        
        self.slotDataChanged()

    ########################################################################
    def __updateObjectFromGUI(self, userobj):
        username = unicode(self.details_tab.loginnameedit.text())
        userobj.setUsername(username)
        userobj.setRealName(unicode(self.details_tab.realnameedit.text()))

        userobj.setHomeDirectory(unicode(self.details_tab.homediredit.text()))
        userobj.setLoginShell(unicode(self.details_tab.shelledit.currentText()))
        self.primarygroupname = \
                    unicode(self.details_tab.primarygroupedit.currentText())
        groupobj =  self.admincontext.lookupGroupname(self.primarygroupname)
        if groupobj is not None:
            userobj.setPrimaryGroup(groupobj)

        # Password expiration.
        if self.pwsec_tab.validradiogroup.checkedId() == 0:
            # Password is always valid.
            userobj.setExpirationDate(None)
        else:
            # Password will expire at...
            userobj.setExpirationDate(QDateToSptime(self.pwsec_tab.expiredate.date()))

        if self.pwsec_tab.forcepasswordchangecheckbox.isChecked():
            userobj.setMaximumPasswordAge(self.pwsec_tab.maximumpasswordedit.value())
        else:
            userobj.setMaximumPasswordAge(None)

        if self.pwsec_tab.disableexpireedit.value() == 0:
            userobj.setPasswordDisableAfterExpire(None)
        else:
            userobj.setPasswordDisableAfterExpire(self.pwsec_tab.disableexpireedit.value())

        if self.pwsec_tab.enforcepasswordminagecheckbox.isChecked():
            userobj.setMinimumPasswordAgeBeforeChange(self.pwsec_tab.minimumpasswordedit.value())
        else:
            userobj.setMinimumPasswordAgeBeforeChange(0)

        userobj.setPasswordExpireWarning(self.pwsec_tab.warningedit.value())

    ########################################################################
    def slotBrowseHomeDirClicked(self):
        fileurl = KUrl()
        fileurl.setPath(self.details_tab.homediredit.text())
        self.homedirdialog.setCurrentUrl(fileurl)
        if self.homedirdialog.exec_()==QDialog.Accepted:
            self.details_tab.homediredit.setText(self.homedirdialog.url().path())
            self.homedirectoryislinked = False

    ########################################################################
    def slotValidUntilToggled(self, expire_on):
        if expire_on:
            self.pwsec_tab.expiredate.setEnabled(True)
        else:
            self.pwsec_tab.expiredate.setEnabled(False)

    ########################################################################
    def slotForcePasswordChangeToggled(self,on):
        on = not on
        self.pwsec_tab.warningedit.setDisabled(on)
        self.pwsec_tab.maximumpasswordedit.setDisabled(on)
        self.pwsec_tab.disableexpireedit.setDisabled(on)

    ########################################################################
    def slotEnforePasswordAgeToggled(self,on):
        self.pwsec_tab.minimumpasswordedit.setDisabled(not on)

    ########################################################################
    def slotDataChanged(self):
        changed = self.isChanged()
        #print self.details_tab.enabledradio.isChecked() , \
                    #self.userobj.isLocked()\
            #, "un", self.details_tab.loginnameedit.text() , \
                  #"un", self.userobj.getUsername()\
            #, "rn",self.details_tab.realnameedit.text() , \
                    #"rn",self.userobj.getRealName()\
            #, self.details_tab.homediredit.text() , \
                    #self.userobj.getHomeDirectory()\
            #, self.details_tab.shelledit.currentText() , \
                #self.userobj.getLoginShell()
        
        if not self.newusermode:
            self.enableButtonOk(changed)
            self.enableButtonApply(changed)
            self.setCaption(i18n("Modifying User Account %1")\
                            .arg(self.userobj.getUsername()),
                            changed)
    
    ########################################################################
    def isChanged(self):
        if not self.newusermode:
            # Kind of ugly.  Hopefully short-circuit evaluation makes it not
            #  too much work.
            # TODO: Primary group
            # UID not included, it can't be modified
            changed = ( self.details_tab.enabledradio.isChecked() ==
                        self.userobj.isLocked()
                or self.details_tab.loginnameedit.text() !=
                        self.userobj.getUsername()\
                or self.details_tab.realnameedit.text() !=
                        self.userobj.getRealName()
                or self.details_tab.primarygroupedit.currentText() !=
                        self.originalprimarygroup.getGroupname()
                or self.details_tab.homediredit.text() !=
                        self.userobj.getHomeDirectory()
                or self.details_tab.shelledit.currentText() !=
                        self.userobj.getLoginShell()
                or [g for g in self.userobj.getGroups()
                        if g is not self.userobj.getPrimaryGroup()] !=
                        self.originalgroups
                or self.pwsec_tab.passwordedit.text() != ""
                or (self.pwsec_tab.validalwaysradio.isChecked()
                    and self.userobj.getExpirationDate() is not None)
                or (self.pwsec_tab.expireradio.isChecked()
                    and (self.userobj.getExpirationDate() !=
                         QDateToSptime(self.pwsec_tab.expiredate.date())))
                or (not self.pwsec_tab.forcepasswordchangecheckbox.isChecked()
                    and self.userobj.getMaximumPasswordAge() is not None)
                or (self.pwsec_tab.forcepasswordchangecheckbox.isChecked()
                    and (self.userobj.getMaximumPasswordAge() !=
                         self.pwsec_tab.maximumpasswordedit.value()
                         or self.userobj.getPasswordExpireWarning() !=
                         self.pwsec_tab.warningedit.value()
                         or (self.userobj.getPasswordDisableAfterExpire()
                             is not None and
                             self.userobj.getPasswordDisableAfterExpire() !=
                             self.pwsec_tab.disableexpireedit.value())
                         or (self.userobj.getPasswordDisableAfterExpire() is
                             None
                             and self.pwsec_tab.disableexpireedit.value() != 0)
                        ))
                or (not self.pwsec_tab.enforcepasswordminagecheckbox.isChecked()
                    and self.userobj.getMinimumPasswordAgeBeforeChange() > 0)
                or (self.pwsec_tab.enforcepasswordminagecheckbox.isChecked()
                    and (self.userobj.getMinimumPasswordAgeBeforeChange() !=
                         self.pwsec_tab.minimumpasswordedit.value()))
                )
            return changed
        else:
            return False

    #######################################################################
    def __fudgeNewGroupName(self,basename):
        if self.admincontext.lookupGroupname(basename) is None:
            return basename
        x = 1
        while self.admincontext.lookupGroupname(basename + u'_' + unicode(x)) is not None:
            x += 1
        return basename + u'_' + unicode(x)

    #######################################################################
    def __fudgeNewHomeDirectory(self,origbasename):
        basename = origbasename.replace("/","")
        if basename=="":
            basename = u"user"

        dhome = self.admincontext.dhome
        if not os.path.isdir(dhome):
            raise OSError, dhome+" does not exist, is it correctly set in "+ \
                    self.admincontext.adduserconf+" ?"
        else:
            # Make sure there's a trailing /
            if dhome[-1] is not '/':
                dhome = dhome+'/'

        if os.path.exists(dhome+basename)==False:
            return dhome+basename
        else:
            x = 1
            while os.path.exists(dhome+basename + u'_' + unicode(x)):
                x += 1
            return dhome+basename



###########################################################################
class LoginNameValidator(QValidator):

    def validate(self,inputstr,pos):
        instr = unicode(inputstr)
        if len(instr)==0:
            return (QValidator.Intermediate,pos)
        for c in instr:
            if ord(c)<0x20 or ord(c)>0x7f or c.isspace() or c==":" or c=="," or c==".":
                return (QValidator.Invalid,pos)

        # Try to encode this string in the system encoding.
        try:
            instr.encode(locale.getpreferredencoding())
        except UnicodeEncodeError:
            # won't encode -> reject it.
            return (QValidator.Invalid,pos)

        return (QValidator.Acceptable,pos)

    #######################################################################
    def fixup(self,inputstr):
        # TODO: TypeError: invalid result type from LoginNameValidator.fixup()
        instr = unicode(inputstr)
        newstr = ""
        for c in instr:
            if (ord(c)<0x20 or ord(c)>0x7f or c.isspace() or c==":" or c=="," or c==".")==False:
                newstr += c

        if newstr=="":
            return "user"
        else:
            return newstr
            

###########################################################################
class RealUserNameValidator(QValidator):

    def validate(self,inputstr,pos):
        instr = unicode(inputstr)
        for c in instr:
            if c==":":
                return (QValidator.Invalid,pos)

        # Try to encode this string in the system encoding.
        try:
            instr.encode(locale.getpreferredencoding())
        except UnicodeEncodeError:
            # won't encode -> reject it.
            return (QValidator.Invalid,pos)

        return (QValidator.Acceptable,pos)

    #######################################################################
    def fixup(self,inputstr):
        return unicode(inputstr).replace(":","")
        
        
###########################################################################
class OverwriteHomeDirectoryDialog(KDialog):
    CANCEL = 0
    OK_KEEP = 1
    OK_REPLACE = 2

    def __init__(self, parent):
        KDialog.__init__(self, parent)
        self.setModal(True)
        self.setCaption(i18n("Create home directory"))
        
        self.updatingGUI = True
        
        self.ui = uic.loadUi('ui/overwritehomedirectory.ui', self.mainWidget())

        # Set up buttons
        self.setButtons(KDialog.ButtonCode(KDialog.Cancel | KDialog.Ok))
        
        self.ui.iconlabel.setPixmap(
            KIconLoader.global_().loadIcon('dialog-warning', KIconLoader.Dialog))

        self.radiogroup = QButtonGroup()
        # Use Existing home directory radio button.
        self.ui.usehomedirectoryradio.setText(
                i18n("Use the existing directory without changing it."))
        # Replace home directory radio button
        self.ui.replacehomedirectoryradio.setText(
                i18n("Delete the directory and replace it with " +
                     "a new home directory."))
        self.radiogroup.addButton(self.ui.usehomedirectoryradio, 0)
        self.radiogroup.addButton(self.ui.replacehomedirectoryradio, 1)
        
        self.updatingGUI = False

    def do(self, userobj):
        """ Executes the dialog.  Sets the text for the top label and defaults
            to using the existing home directory.  Returns a result code.
        """
        self.ui.toplabel.setText(i18n("The directory '%1' was entered as the " +
            "home directory for new user '%2'.\n" +
            "This directory already exists.")\
            .arg(userobj.getHomeDirectory()).arg(userobj.getUsername()) )
        self.radiogroup.button(0).setChecked(True)

        if self.exec_() == QDialog.Accepted:
            if self.radiogroup.checkedId() == 0:
                return OverwriteHomeDirectoryDialog.OK_KEEP
            else:
                return OverwriteHomeDirectoryDialog.OK_REPLACE
        else:
            return OverwriteHomeDirectoryDialog.CANCEL
        

###########################################################################

class UserDeleteDialog(KPageDialog):
    def __init__(self,parent,admincontext):
        KPageDialog.__init__(self,parent)
        if os.path.exists('ui/deleteuserdialog.ui'): 
            self.up = uic.loadUi('ui/deleteuserdialog.ui', self)

        self.setModal(True) #,Qt.WType_Dialog)
        self.setCaption(i18n("Delete User Account"))
        self.admincontext = admincontext
        self.updatingGUI = True

        #toplayout = QVBoxLayout(self)
        #toplayout = QGridLayout(self)
        #toplayout.setSpacing(self.spacingHint())
        #toplayout.setMargin(self.marginHint())

        #contentbox = KHBox(self)
        #contentbox.setSpacing(self.spacingHint())
        #toplayout.addWidget(contentbox)
        #toplayout.setStretchFactor(contentbox,1)

        #label = QLabel(contentbox)
        #label.setPixmap(KGlobal.iconLoader().loadIcon("messagebox_warning", KIcon.NoGroup, KIcon.SizeMedium,
            #KIcon.DefaultState, None, True)) # TODO:
        #contentbox.setStretchFactor(label,0)

        #textbox = KVBox(contentbox)

        #textbox.setSpacing(self.spacingHint())
        #textbox.setMargin(self.marginHint())

        #self.usernamelabel = QLabel("",textbox)
        #textbox.setStretchFactor(self.usernamelabel,0)

        # Remove directory checkbox.
        #self.deletedirectorycheckbox = QCheckBox(i18n("Delete home directory ()"),textbox)
        #textbox.setStretchFactor(self.deletedirectorycheckbox,0)

        # Delete the User's private group.
        #self.deletegroupcheckbox = QCheckBox(i18n("Delete group ()"),textbox)
        #textbox.setStretchFactor(self.deletegroupcheckbox ,0)

        # Buttons
        #buttonbox = KHBox(self)
        #toplayout.addWidget(buttonbox)

        #buttonbox.setSpacing(self.spacingHint())
        #toplayout.setStretchFactor(buttonbox,0)

        #spacer = QWidget(buttonbox)
        #buttonbox.setStretchFactor(spacer,1)

        #okbutton = QPushButton(i18n("OK"),buttonbox)
        #buttonbox.setStretchFactor(okbutton,0)
        #self.connect(okbutton,SIGNAL("clicked()"),self.slotOkClicked)

        #cancelbutton = QPushButton(i18n("Cancel"),buttonbox)
        #cancelbutton.setDefault(True)
        #buttonbox.setStretchFactor(cancelbutton,0)
        #self.connect(cancelbutton,SIGNAL("clicked()"),self.slotCancelClicked)

    def deleteUser(self,userid):
        # Setup the 
        userobj = self.admincontext.lookupUID(userid)
        self.usernamelabel.setText(i18n("Are you sure want to delete user account '%1' (%2)?").arg(userobj.getUsername()).arg(userobj.getUID()) )
        self.deletedirectorycheckbox.setChecked(False)
        self.deletedirectorycheckbox.setText(i18n("Delete home directory (%1)").arg(userobj.getHomeDirectory()))
        primarygroupobj = userobj.getPrimaryGroup()
        primarygroupname = primarygroupobj.getGroupname()
        self.deletegroupcheckbox.setText(i18n("Delete group '%1' (%2)").arg(primarygroupname).arg(primarygroupobj.getGID()))
        self.deletegroupcheckbox.setChecked(len(primarygroupobj.getUsers())==1)
        if self.exec_()==QDialog.Accepted:
            self.admincontext.removeUser(userobj)
            if self.deletedirectorycheckbox.isChecked():
                self.admincontext.removeHomeDirectory(userobj)
                # FIXME
                #self.admincontext.removeMail(userobj)
            if self.deletegroupcheckbox.isChecked():
                self.admincontext.removeGroup(primarygroupobj)
            self.admincontext.save()
            return True
        else:
            return False

    def slotOkClicked(self):
        self.accept()

    def slotCancelClicked(self):
        self.reject()

