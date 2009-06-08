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
from models import GroupListModel, PrivilegeListProxyModel

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
        
        self.groups_model = GroupListModel(None,
                                        self.admincontext.getGroups(),
                                        self.userobj)
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
        self.connect(self.pwsec_tab.validradiogroup,
                     SIGNAL("clicked(int)"),
                     self.slotValidUntilClicked)

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
        
        self.pwsec_tab.passwordedit.clear()
        
        # Save the secondary groups so they can be restored
        originalgroups = [g for g in self.userobj.getGroups()
                                if g is not self.userobj.getPrimaryGroup()]
        
        # FIXME we should repopulate the groups
        # privileges list when the primary group is changed in the other tab --
        # that is, on the change slot of the primary group drop down.
        self.groups_model.setUser(self.userobj)
        
        # Puts most of the user data into the GUI
        self.__syncGUI()
        
        self.details_tab.uidedit.setReadOnly(True)
        
        self.updatingGUI = False
        self.homedirectoryislinked = False
        
        if self.exec_() == QDialog.Accepted:
            # Put in most of the data
            self.__updateObjectFromGUI(self.userobj)
            
            # Set the password.
            if self.pwsec_tab.passwordedit.text()!="":
                self.userobj.setPassword(str(self.pwsec_tab.passwordedit.text()))
            
            # Secondary groups are updated within the model, nothing to do here
            #  if dialog accepted, need to revert if rejected.

            # __updateObjectFromGUI tries to set the primary group, but won't
            #  set it if the group doesn't exist yet
            # TODO: ask for confirmation
            if self.admincontext.lookupGroupname(self.primarygroupname) is None:
                # Create a new group
                newgroup = self.admincontext.newGroup(True)
                newgroup.setGroupname(self.primarygroupname)
                self.admincontext.addGroup(newgroup)
                self.userobj.setPrimaryGroup(newgroup)

            # Enable/Disable the account
            self.userobj.setLocked(
                self.details_tab.enabledradiogroup.checkedId() != 0)
            
            # Save everything
            self.admincontext.save()
            
            return self.userobj.getUID()
        else: # Dialog rejected
            # Revert secondary groups, since those are being stored in the user
            #  by the model
            # FIXME: might be borked if primary group is changed
            currentgroups = [g for g in self.userobj.getGroups()
                                   if g is not self.userobj.getPrimaryGroup()]
            addedgroups = [g for g in currentgroups
                               if g not in originalgroups]
            removedgroups = [g for g in originalgroups
                               if g not in currentgroups]
            for group in removedgroups:
                self.userobj.addToGroup(group)
            for group in addedgroups:
                self.userobj.removeFromGroup(group)
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
        # FIXME we should repopulate the groups privileges list when the
        # primary group is changed in the other tab -- that is, on the change
        # slot of the primary group drop down.
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
        
        if self.exec_() == QDialog.Accepted:
            # Put in most of the data
            self.__updateObjectFromGUI(self.userobj)

            # Decide what to do about the home directory
            makehomedir = True
            deleteoldhomedir = False
            if os.path.exists(self.userobj.getHomeDirectory()):
                rc = self.createhomedirectorydialog.do(self.userobj)
                if rc == OverwriteHomeDirectoryDialog.CANCEL:
                    return None
                if rc == OverwriteHomeDirectoryDialog.OK_KEEP:
                    makehomedir = False
                elif rc == OverwriteHomeDirectoryDialog.OK_REPLACE:
                    deleteoldhomedir = True

            # Add the user to the admin context.  Before this the userobj
            #  exists on its own.
            self.admincontext.addUser(self.userobj)

            # __updateObjectFromGUI tries to set the primary group, but won't
            #  set it if the group doesn't exist yet
            if self.admincontext.lookupGroupname(self.primarygroupname) is None:
                # Create a new group
                newgroup = self.admincontext.newGroup(True)
                newgroup.setGroupname(self.primarygroupname)
                self.admincontext.addGroup(newgroup)
                self.userobj.setPrimaryGroup(newgroup)

            # Secondary groups are updated within the model, nothing to do here

            # Set the password.
            # if self.passwordedit.password()!="":
            if self.pwsec_tab.passwordedit.text() != "":
                 self.userobj.setPassword(str(self.passwordedit.text()))

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

            return self.userobj.getUID()
        else: # Dialog rejected
            return None

    ########################################################################
    def slotOk(self):
        ok = True
        # Sanity check all values.
        if self.newusermode:
            newusername = unicode(self.details_tab.realnameedit.text())
            if self.admincontext.lookupUsername(newusername)!=None:
                KMessageBox.sorry(self,i18n("Sorry, you must choose a different user name.\n'%1' is already being used.").arg(newusername))
                ok = False
            else:
                newuid = int(unicode(self.uidedit.text()))
                originaluid = self.userobj.getUID()
                if self.admincontext.lookupUID(newuid)!=None:
                    rc = KMessageBox.questionYesNo(self,i18n("User ID in use"),
                        i18n("Sorry, the UID %1 is already in use. Should %2 be used instead?").arg(newuid).arg(originaluid))
                    if rc==KMessageBox.Yes:
                        self.uidedit.setValue(unicode(originaluid))
                    else:
                        ok = False
                else:
                    self.userobj.setUID(newuid)
        if ok:
            self.passwordedit.clear()
            KDialogBase.slotOk(self)

    ########################################################################
    def slotLoginChanged(self,text):
        newtext = unicode(text)
        if not self.updatingGUI:
            if self.newusermode:
                self.newprimarygroupname = self.__fudgeNewGroupName(newtext)
                self.updatingGUI = True
                #self.up.primarygroupedit.setItemText(self.newprimarygroupname,0) FIXME! Doesn't work...
                if self.homedirectoryislinked:
                    homedir = self.__fudgeNewHomeDirectory(newtext)
                    self.details_tab.homediredit.setText(homedir)
                self.updatingGUI = False

    ########################################################################
    def slotHomeDirChanged(self,text):
        if self.updatingGUI==False:
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
        self.details_tab.primarygroupedit.clear()
        allgroups = [g.getGroupname() for g in self.admincontext.getGroups()]
        allgroups.sort()

        if self.newusermode:
            # New user mode
            self.newprimarygroupname = \
                self.__fudgeNewGroupName(unicode(self.userobj.getUsername()))
            primarygroupname = self.newprimarygroupname
            self.details_tab.primarygroupedit.addItem(self.newprimarygroupname)
        else:
            # Existing user mode
            primarygroupname = self.userobj.getPrimaryGroup().getGroupname()
        for group in allgroups:
            self.details_tab.primarygroupedit.addItem(group)
        self.details_tab.primarygroupedit.setEditText(primarygroupname)

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
            self.pwsec_tab.maximumpasswordedit.setValue(self.userobj.getMaximumPasswordAge())

        if self.userobj.getPasswordDisableAfterExpire() is None:
            self.pwsec_tab.disableexpireedit.setValue(0)
        else:
            self.pwsec_tab.disableexpireedit.setValue(self.userobj.getPasswordDisableAfterExpire())

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

    ########################################################################
    def __updateObjectFromGUI(self,userobj):
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
        if self.pwsec_tab.validradiogroup.id(self.pwsec_tab.validradiogroup.checkedButton())==0:
            # Password is always valid.
            userobj.setExpirationDate(None)
        else:
            # Password will expire at...
            userobj.setExpirationDate(QDateToSptime(self.expiredate.date()))

        if self.pwsec_tab.forcepasswordchangecheckbox.isChecked():
            userobj.setMaximumPasswordAge(self.maximumpasswordedit.value())
        else:
            userobj.setMaximumPasswordAge(None)

        if self.pwsec_tab.disableexpireedit.value()==0:
            userobj.setPasswordDisableAfterExpire(None)
        else:
            userobj.setPasswordDisableAfterExpire(self.disableexpireedit.value())

        if self.pwsec_tab.enforcepasswordminagecheckbox.isChecked():
            userobj.setMinimumPasswordAgeBeforeChange(self.minimumpasswordedit.value())
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
    def slotValidUntilClicked(self,id):
        if id==0:
            self.expiredate.setDisabled(True)
        else:
            self.expiredate.setDisabled(False)

    ########################################################################
    def slotForcePasswordChangeToggled(self,on):
        on = not on
        self.pwsec_tab.warningedit.setDisabled(on)
        self.pwsec_tab.maximumpasswordedit.setDisabled(on)
        self.pwsec_tab.disableexpireedit.setDisabled(on)

    ########################################################################
    def slotEnforePasswordAgeToggled(self,on):
        self.pwsec_tab.minimumpasswordedit.setDisabled(not on)

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

