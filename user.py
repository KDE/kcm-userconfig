#!/usr/bin/python
# -*- coding: UTF-8 -*-
###########################################################################
# userconfig.py - description                                             #
# ------------------------------                                          #
# begin     : Wed Apr 30 2003                                             #
# copyright : (C) 2003-2006 by Simon Edwards, 2008 by Yuriy Kozlov        #
# email     : simon@simonzone.com                                         #
#                                                                         #
###########################################################################
#                                                                         #
#   This program is free software; you can redistribute it and/or modify  #
#   it under the terms of the GNU General Public License as published by  #
#   the Free Software Foundation; either version 2 of the License, or     #
#   (at your option) any later version.                                   #
#                                                                         #
###########################################################################

# Qt imports
from PyQt4.QtGui import *
from PyQt4.QtCore import *

# KDE imports
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.kio import *

class UserEditDialog(KPageDialog):
    def __init__(self,parent,admincontext):
        #KDialogBase.__init__(self,KJanusWidget.Tabbed,i18n("User Account"),KDialogBase.Ok|KDialogBase.Cancel,
            #KDialogBase.Cancel,parent)
        KPageDialog.__init__( self, parent )
        self.setFaceType( KPageDialog.Tabbed )
        #self.setObjectName( name )
        self.setModal( True )
        self.setCaption( i18n( "User Account" ) )
        #self.setButtons( KDialog.Ok|KDialog.Cancel) # TODO

        self.admincontext = admincontext
        self.updatingGUI = True

        detailshbox = KHBox(self)
        item = self.addPage( detailshbox, i18n( "Details" ) )
        item.setHeader( i18n( "Details" ) )
        detailspace = QWidget(detailshbox)

        infogrid = QGridLayout(detailspace)
        infogrid.setSpacing(self.spacingHint())
        #infogrid.setColStretch(0,0)
        #infogrid.setColStretch(1,1)

        self.enabledradiogroup = QButtonGroup()
        #self.enabledradiogroup.setRadioButtonExclusive(True)
        hb = KHBox(detailspace)
        hb.setSpacing(self.spacingHint())
        label = QLabel(hb)
        label.setPixmap(UserIcon("hi32-identity"))
        hb.setStretchFactor(label,0)
        label = QLabel(i18n("Status:"),hb)
        hb.setStretchFactor(label,1)
        infogrid.addWidget(hb,0,1,0,0)

        self.enabledradio = QRadioButton(i18n("Enabled"),detailspace)
        infogrid.addWidget(self.enabledradio,0,1)

        hbox = KHBox(detailspace)
        hbox.setSpacing(self.spacingHint())
        self.disabledradio = QRadioButton(i18n("Disabled"),hbox)
        hbox.setStretchFactor(self.disabledradio,0)
        label = QLabel(hbox)
        label.setPixmap(UserIcon("hi16-encrypted"))
        hbox.setStretchFactor(label,1)        
        infogrid.addWidget(hbox,1,1)

        self.enabledradiogroup.addButton(self.enabledradio,0)
        self.enabledradiogroup.addButton(self.disabledradio,1)

        label = QLabel(i18n("Login Name:"),detailspace)
        infogrid.addWidget(label,2,0)
        self.loginnameedit = KLineEdit("",detailspace)
        self.loginnameedit.setValidator(LoginNameValidator(self.loginnameedit))

        infogrid.addWidget(self.loginnameedit,2,1)
        self.connect(self.loginnameedit, SIGNAL("textChanged(const QString &)"), self.slotLoginChanged)

        label = QLabel(i18n("Real Name:"),detailspace)
        infogrid.addWidget(label,3,0)
        self.realnameedit = KLineEdit("",detailspace)
        self.realnameedit.setValidator(RealUserNameValidator(self.realnameedit))

        infogrid.addWidget(self.realnameedit,3,1)

        label = QLabel(i18n("User ID:"),detailspace)
        infogrid.addWidget(label,4,0)
        self.uidedit = KLineEdit("",detailspace)
        self.uidedit.setValidator(QIntValidator(0,65535,detailspace))
        infogrid.addWidget(self.uidedit,4,1)

        label = QLabel(i18n("Primary Group:"),detailspace)
        infogrid.addWidget(label,5,0)
        self.primarygroupedit = KComboBox(False,detailspace)
        infogrid.addWidget(self.primarygroupedit,5,1)

        label = QLabel(i18n("Home Directory:"),detailspace)
        infogrid.addWidget(label,7,0)

        hbox = KHBox(detailspace)
        hbox.setSpacing(self.spacingHint())
        self.homediredit = KLineEdit("",hbox)
        hbox.setStretchFactor(self.homediredit,1)
        self.connect(self.homediredit, SIGNAL("textChanged(const QString &)"), self.slotHomeDirChanged)
        self.homedirbutton = KPushButton(i18n("Browse..."),hbox)
        hbox.setStretchFactor(self.homedirbutton,0)
        self.connect(self.homedirbutton,SIGNAL("clicked()"),self.slotBrowseHomeDirClicked)
        infogrid.addWidget(hbox,7,1)

        label = QLabel(i18n("Shell:"),detailspace)
        infogrid.addWidget(label,8,0)

        self.shelledit = KComboBox(True,detailspace)
        for shell in self.admincontext.getUserShells():
            self.shelledit.addItem(shell)
        infogrid.addWidget(self.shelledit,8,1)

        # Rudd-O rules.  Not so much, but enough to rule.
        # yeah it's not my finest hour, but it works like a charm over here.  Please feel free to clean up dead code that I commented
        # I extend my deepest thanks to the people that have worked hard to construct this tool in the first place.  I have no idea who the authors and contributors are, but it would make sense to have all the contributors listed on top of the file.
        # Privileges and groups tab
        groupshbox = KHBox(self)
        item = self.addPage( groupshbox, i18n( "Privileges and groups" ) )
        item.setHeader( i18n( "Privileges and groups" ) )

        # Rudd-O now here we create the widget that will hold the group listing, and fill it with the groups.
        self.privilegeslistview = QListView(groupshbox)
        #self.privilegeslistview.addColumn(i18n("Privilege"),-1)
        self.groupslistview = QListView(groupshbox)
        #self.groupslistview.addColumn(i18n("Secondary group"),-1)
        groupshbox.setStretchFactor(self.privilegeslistview,3)
        groupshbox.setStretchFactor(self.groupslistview,2)
    
        # Password and Security Tab.
        passwordvbox = KVBox(self)
        item = self.addPage( passwordvbox, i18n( "Password && Security" ))
        item.setHeader( i18n("Password && Security" ))

        passwordspace = QWidget(passwordvbox)
        passwordgrid = QGridLayout(passwordspace)
        passwordgrid.setSpacing(self.spacingHint())
        #passwordgrid.setColStretch(0,0)
        #passwordgrid.setColStretch(1,0)
        #passwordgrid.setColStretch(2,1)
        passwordvbox.setStretchFactor(passwordspace,0)

        hb = KHBox(passwordspace)
        hb.setSpacing(self.spacingHint())
        label = QLabel(hb)
        label.setPixmap(UserIcon("hi32-password"))
        hb.setStretchFactor(label,0)
        label = QLabel(i18n("Password:"),hb)
        hb.setStretchFactor(label,1)
        passwordgrid.addWidget(hb,0,0)

        self.passwordedit = KLineEdit(passwordspace)
        self.passwordedit.setPasswordMode(True)
        passwordgrid.addWidget(self.passwordedit,0,1)

        # Last Change
        label = QLabel(i18n("Last changed:"),passwordspace)
        passwordgrid.addWidget(label,1,0)
        self.lastchangelabel = KLineEdit("",passwordspace)
        self.lastchangelabel.setReadOnly(True)
        passwordgrid.addWidget(self.lastchangelabel,1,1)

        self.validradiogroup = QButtonGroup()
        #self.validradiogroup.setRadioButtonExclusive(True) # TODO

        # Valid until.
        label = QLabel(i18n("Valid until:"),passwordspace)
        passwordgrid.addWidget(label,2,0)
        self.validalwaysradio = QRadioButton(i18n("Always"),passwordspace)
        passwordgrid.addWidget(self.validalwaysradio,2,1)

        hbox = KHBox(passwordspace)
        hbox.setSpacing(self.spacingHint())
        self.expireradio = QRadioButton(hbox)
        hbox.setStretchFactor(self.expireradio,0)

        self.expiredate = KDateWidget(hbox)
        hbox.setStretchFactor(self.expiredate,1)
        passwordgrid.addWidget(hbox,3,1)

        self.validradiogroup.addButton(self.validalwaysradio,0)
        self.validradiogroup.addButton(self.expireradio,1)
        self.connect(self.validradiogroup,SIGNAL("clicked(int)"),self.slotValidUntilClicked)

        # Password Aging & Expiration.
        passwordaginggroup = QGroupBox(i18n("Password Aging"),passwordvbox)
        passwordagingbox = KVBox(passwordaginggroup)
        #passwordagingbox.setInsideSpacing(self.spacingHint())
        passwordvbox.setStretchFactor(passwordagingbox,0)

        passwordagingwidget = QWidget(passwordagingbox)

        passwordaginggrid = QGridLayout(passwordagingwidget)
        passwordaginggrid.setSpacing(self.spacingHint())

        # [*] Require new password after: [_____5 days]
        self.forcepasswordchangecheckbox = QCheckBox(passwordagingwidget)
        self.connect(self.forcepasswordchangecheckbox,SIGNAL("toggled(bool)"),self.slotForcePasswordChangeToggled)
        passwordaginggrid.addWidget(self.forcepasswordchangecheckbox,0,0)
        label = QLabel(i18n("Require new password after:"),passwordagingwidget)
        passwordaginggrid.addWidget(label,0,1) 
        self.maximumpasswordedit = QSpinBox(passwordagingwidget)
        self.maximumpasswordedit.setSuffix(i18n(" days"))
        self.maximumpasswordedit.setMinimum(1)
        self.maximumpasswordedit.setMaximum(365*5)
        passwordaginggrid.addWidget(self.maximumpasswordedit,0,2)

        label = QLabel(i18n("Warn before password expires:"),passwordagingwidget)
        passwordaginggrid.addWidget(label,1,1)
        self.warningedit = QSpinBox(passwordagingwidget)
        self.warningedit.setPrefix(i18n("After "))
        self.warningedit.setSuffix(i18n(" days"))
        self.warningedit.setMinimum(0)
        self.warningedit.setMaximum(365*5)
        self.warningedit.setSpecialValueText(i18n("Never"))
        passwordaginggrid.addWidget(self.warningedit,1,2)

        label = QLabel(i18n("Disable account after password expires:"),passwordagingwidget)
        passwordaginggrid.addWidget(label,2,1)
        self.disableexpireedit = QSpinBox(passwordagingwidget)
        self.disableexpireedit.setPrefix(i18n("After "))
        self.disableexpireedit.setSuffix(i18n(" days"))
        self.disableexpireedit.setMinimum(0)
        self.disableexpireedit.setMaximum(365*5)
        self.disableexpireedit.setSpecialValueText(i18n("Never"))
        passwordaginggrid.addWidget(self.disableexpireedit,2,2)

        self.enforcepasswordminagecheckbox = QCheckBox(passwordagingwidget)
        self.connect(self.enforcepasswordminagecheckbox,SIGNAL("toggled(bool)"),self.slotEnforePasswordAgeToggled)
        passwordaginggrid.addWidget(self.enforcepasswordminagecheckbox,3,0)

        label = QLabel(i18n("Enforce minimum password age:"),passwordagingwidget)
        passwordaginggrid.addWidget(label,3,1)
        self.minimumpasswordedit = QSpinBox(passwordagingwidget)
        self.minimumpasswordedit.setSuffix(i18n(" days"))
        passwordaginggrid.addWidget(self.minimumpasswordedit,3,2)

        spacer = QWidget(passwordvbox)
        passwordvbox.setStretchFactor(spacer,1)

        self.homedirdialog = KDirSelectDialog(KUrl.fromPath("/"),True,self)
        self.createhomedirectorydialog = OverwriteHomeDirectoryDialog(None)
        self.updatingGUI = False

    def _repopulateGroupsPrivileges(self,excludegroups=None):
        # needs listviews to be constructed.  Expects a list of PwdGroups to be excluded
        
        # rehash everything
        self.privilegeslistview.clear()
        self.groupslistview.clear()
        self.secondarygroupcheckboxes = {}
        pn = PrivilegeNames()
        
        if excludegroups: excludegroups = [ g.getGroupname() for g in excludegroups ]
        else: excludegroups = []
        for group in [g.getGroupname() for g in self.admincontext.getGroups()]:
            if group in excludegroups: continue
            if group in pn:
                name = i18n(unicode(pn[group]).encode(locale.getpreferredencoding()))
                wid = self.privilegeslistview
            else:
                name = unicode(group).encode(locale.getpreferredencoding())
                wid = self.groupslistview
            self.secondarygroupcheckboxes[group] = QCheckListItem(wid,name,QCheckListItem.CheckBox)

    ########################################################################
    def showEditUser(self,userid):
        self.updatingGUI = True
        self.newusermode = False
        self.userobj = self.admincontext.lookupUID(userid)
        self.userid = userid
        self.passwordedit.erase()
        self.selectedgroups = [g.getGroupname() for g in self.userobj.getGroups()
            if g is not self.userobj.getPrimaryGroup()]
        
        # Rudd-O: now here we tick the appropriate group listing checkbox, and hide the currently active primary group of the user.  We are repopulating because if the user to edit changes, we need to hide the user's secondary group.  FIXME we should repopulate the groups privileges list when the primary group is changed in the other tab -- that is, on the change slot of the primary group drop down.
        self._repopulateGroupsPrivileges(excludegroups=[self.userobj.getPrimaryGroup()])
        for group,checkbox in self.secondarygroupcheckboxes.items():
            if group in self.selectedgroups: checkbox.setState(QCheckListItem.On)
            else: checkbox.setState(QCheckListItem.Off)
        
        self.originalgroups = self.selectedgroups[:]
        self.selectedgroups.sort()
        self.__syncGUI()
        self.uidedit.setReadOnly(True)
        self.updatingGUI = False
        self.homedirectoryislinked = False
        if self.exec_()==QDialog.Accepted:
            self.__updateObjectFromGUI(self.userobj)
            # Set the password.
            if self.passwordedit.password()!="":
                self.userobj.setPassword(self.passwordedit.password())
            # Update the groups for this user object. Rudd-O here's when you go in, stud.
        # we collect the selected groups
        self.selectedgroups = [ group for group,checkbox in self.secondarygroupcheckboxes.items() if checkbox.isOn() ]

        for g in self.userobj.getGroups(): # this seems wasteful to remove the user from all groups then re-add, why not a cross check?
            self.userobj.removeFromGroup(g)
        for gn in self.selectedgroups:
            self.userobj.addToGroup(self.admincontext.lookupGroupname(gn))

        primarygroupname = unicode(self.primarygroupedit.currentText())
        self.userobj.setPrimaryGroup(self.admincontext.lookupGroupname(primarygroupname))

        # Enable/Disable the account            
        self.userobj.setLocked(self.enabledradiogroup.id(self.enabledradiogroup.selected())!=0)
        self.admincontext.save()

    ########################################################################
    def showNewUser(self):
        self.updatingGUI = True
        self.newusermode = True
        self.userobj = self.admincontext.newUser(True)

        self.newgroup = self.admincontext.newGroup(True)
        self.newgroup.setGroupname(self.__fudgeNewGroupName(self.userobj.getUsername()))
        self.userobj.setPrimaryGroup(self.newgroup)

        self.selectedgroups = [ u'dialout',u'cdrom',u'floppy',u'audio',u'video',
                                u'plugdev',u'lpadmin',u'scanner']
        homedir = self.__fudgeNewHomeDirectory(self.userobj.getUsername())
        
        # Rudd-O FIXME: now here we tick the proper groups that should be allowed.  Now it selects what userconfig selected before.  FIXME consider adding a drop down that will select the appropriate profile Limited User, Advanced User or Administrator (and see if there is a config file where these profiles can be read).    We are repopulating because if the user to edit changes, we need to hide the user's secondary group.  FIXME we should repopulate the groups privileges list when the primary group is changed in the other tab -- that is, on the change slot of the primary group drop down.
        self._repopulateGroupsPrivileges()
        for group,checkbox in self.secondarygroupcheckboxes.items():
            if group in self.selectedgroups: checkbox.setState(QCheckListItem.On)
            else: checkbox.setState(QCheckListItem.Off)
        
        self.userobj.setHomeDirectory(homedir)
        self.homediredit.setText(homedir)

        shells = self.admincontext.getUserShells()
        dshell = self.admincontext.dshell
        if dshell and (dshell in shells):
            self.userobj.setLoginShell(dshell)
        elif '/bin/bash' in shells:
            self.userobj.setLoginShell('/bin/bash')
        elif '/bin/sh' in shells:
            self.userobj.setLoginShell('/bin/sh')        
        elif len(shells)!=0:
            self.userobj.setLoginShell(shells[0])            

        self.__syncGUI()

        self.uidedit.setReadOnly(False)
        self.updatingGUI = False
        self.homedirectoryislinked = True
        self.passwordedit.erase()
        if self.exec_()==QDialog.Accepted:
            self.__updateObjectFromGUI(self.userobj)

            makehomedir = True
            deleteoldhomedir = False

            if os.path.exists(self.userobj.getHomeDirectory()):
                rc = self.createhomedirectorydialog.do(self.userobj)
                if rc==OverwriteHomeDirectoryDialog.CANCEL:
                    return None
                if rc==OverwriteHomeDirectoryDialog.OK_KEEP:
                    makehomedir = False
                else:
                    deleteoldhomedir = True

            self.admincontext.addUser(self.userobj)

            if self.admincontext.lookupGroupname(self.primarygroupname) is None:
                # Create a new group
                newgroup = self.admincontext.newGroup(True)
                newgroup.setGroupname(self.primarygroupname)
                self.admincontext.addGroup(newgroup)
                self.userobj.setPrimaryGroup(newgroup)

            # Update the groups for this user object. Rudd-O here's when you go in, stud.
            # we collect the selected groups
            self.selectedgroups = [ group for group,checkbox in self.secondarygroupcheckboxes.items() if checkbox.isOn() ]
            for gn in self.selectedgroups:
                self.userobj.addToGroup(self.admincontext.lookupGroupname(gn))

            # Set the password.
            if self.passwordedit.password()!="":
                self.userobj.setPassword(self.passwordedit.password())

            # Enable/Disable the account            
            self.userobj.setLocked(self.enabledradiogroup.id(self.enabledradiogroup.selected())!=0)
            self.admincontext.save()

            if deleteoldhomedir:
                if os.path.exists(self.userobj.getHomeDirectory()):
                    shutil.rmtree(self.userobj.getHomeDirectory())
            if makehomedir:
                self.admincontext.createHomeDirectory(self.userobj)

            return self.userobj.getUID()
        else:
            return None

    ########################################################################
    def slotOk(self):
        ok = True
        # Sanity check all values.
        if self.newusermode:
            newusername = unicode(self.realnameedit.text())
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
                self.primarygroupedit.changeItem(self.newprimarygroupname,0)
                if self.homedirectoryislinked:
                    homedir = self.__fudgeNewHomeDirectory(newtext)
                    self.homediredit.setText(homedir)
                self.updatingGUI = False

    ########################################################################
    def slotHomeDirChanged(self,text):
        if self.updatingGUI==False:
            self.homedirectoryislinked = False

    ########################################################################
    def __syncGUI(self):
        if self.userobj.isLocked():
            self.enabledradiogroup.setButton(1)
        else:
            self.enabledradiogroup.setButton(0)

        self.loginnameedit.setText(self.userobj.getUsername())
        self.realnameedit.setText(self.userobj.getRealName())
        self.uidedit.setText(unicode(self.userobj.getUID()))
        self.homediredit.setText(self.userobj.getHomeDirectory())
        self.shelledit.setCurrentText(self.userobj.getLoginShell())

        # Primary Group
        self.primarygroupedit.clear()
        allgroups = [g.getGroupname() for g in self.admincontext.getGroups()]
        allgroups.sort()
        self.availablegroups = allgroups[:]

        try:
            self.availablegroups.remove(self.userobj.getPrimaryGroup().getGroupname())
        except ValueError:
            pass

        if self.newusermode:
            # New user mode
            self.newprimarygroupname = self.__fudgeNewGroupName(unicode(self.userobj.getUsername()))
            primarygroupname = self.newprimarygroupname
            self.primarygroupedit.insertItem(self.newprimarygroupname)
        else:
            # Existing user mode
            primarygroupname = self.userobj.getPrimaryGroup().getGroupname()
        for group in allgroups:
            self.primarygroupedit.insertItem(group)
        self.primarygroupedit.setCurrentText(primarygroupname)

        # If ShadowExpire is turn off then we change the radio box.
        if self.userobj.getExpirationDate() is None:
            self.validradiogroup.setButton(0)
            self.expiredate.setDisabled(True)
            self.expiredate.setDate(SptimeToQDate(99999L))
        else:
            self.validradiogroup.setButton(1)
            self.expiredate.setDisabled(False)
            self.expiredate.setDate(SptimeToQDate(self.userobj.getExpirationDate()))

        if self.userobj.getMaximumPasswordAge() is None:
            # Password aging is turn off
            self.forcepasswordchangecheckbox.setChecked(False)
            d = True
        else:
            # Password aging is turn on
            self.forcepasswordchangecheckbox.setChecked(True)
            d = False
        self.warningedit.setDisabled(d)
        self.maximumpasswordedit.setDisabled(d)
        self.disableexpireedit.setDisabled(d)

        if self.userobj.getPasswordExpireWarning() is None:
            self.warningedit.setValue(0)
        else:
            self.warningedit.setValue(self.userobj.getPasswordExpireWarning())

        if self.userobj.getMaximumPasswordAge() is None:
            self.maximumpasswordedit.setValue(30)
        else:
            self.maximumpasswordedit.setValue(self.userobj.getMaximumPasswordAge())

        if self.userobj.getPasswordDisableAfterExpire() is None:
            self.disableexpireedit.setValue(0)
        else:
            self.disableexpireedit.setValue(self.userobj.getPasswordDisableAfterExpire())

        minage = self.userobj.getMinimumPasswordAgeBeforeChange()
        self.enforcepasswordminagecheckbox.setChecked(minage>0)
        self.minimumpasswordedit.setDisabled(minage<=0)
        if minage<=0:
            minage = 1
        self.minimumpasswordedit.setValue(minage)

        if self.userobj.getLastPasswordChange() in (None,0):
            self.lastchangelabel.setText('-');
        else:
            self.lastchangelabel.setText(KGlobal.locale().formatDate(SptimeToQDate(int(self.userobj.getLastPasswordChange()))))

    ########################################################################
    def __updateObjectFromGUI(self,userobj):
        username = unicode(self.loginnameedit.text())
        userobj.setUsername(username)
        userobj.setRealName(unicode(self.realnameedit.text()))

        userobj.setHomeDirectory(unicode(self.homediredit.text()))
        userobj.setLoginShell(unicode(self.shelledit.currentText()))
        self.primarygroupname = unicode(self.primarygroupedit.currentText())
        groupobj =  self.admincontext.lookupGroupname(self.primarygroupname)
        if groupobj is not None:
            userobj.setPrimaryGroup(groupobj)

        # Password expiration.
        if self.validradiogroup.id(self.validradiogroup.selected())==0:
            # Password is always valid.
            userobj.setExpirationDate(None)
        else:
            # Password will expire at...
            userobj.setExpirationDate(QDateToSptime(self.expiredate.date()))

        if self.forcepasswordchangecheckbox.isChecked():
            userobj.setMaximumPasswordAge(self.maximumpasswordedit.value())
        else:
            userobj.setMaximumPasswordAge(None)

        if self.disableexpireedit.value()==0:
            userobj.setPasswordDisableAfterExpire(None)
        else:
            userobj.setPasswordDisableAfterExpire(self.disableexpireedit.value())

        if self.enforcepasswordminagecheckbox.isChecked():
            userobj.setMinimumPasswordAgeBeforeChange(self.minimumpasswordedit.value())
        else:
            userobj.setMinimumPasswordAgeBeforeChange(0)

        userobj.setPasswordExpireWarning(self.warningedit.value())

    ########################################################################
    def slotBrowseHomeDirClicked(self):
        fileurl = KURL()
        fileurl.setPath(self.homediredit.text())
        self.homedirdialog.setCurrentURL(fileurl)
        if self.homedirdialog.exec_()==QDialog.Accepted:
            self.homediredit.setText(self.homedirdialog.url().path())
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
        self.warningedit.setDisabled(on)
        self.maximumpasswordedit.setDisabled(on)
        self.disableexpireedit.setDisabled(on)

    ########################################################################
    def slotEnforePasswordAgeToggled(self,on):
        self.minimumpasswordedit.setDisabled(not on)

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
    def __init__(self,parent):
        QValidator.__init__(self,parent)

    #######################################################################
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
    def __init__(self,parent):
        QValidator.__init__(self,parent)

    #######################################################################
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

    def __init__(self,parent):
        KDialog.__init__(self,parent)
        self.setModal(True)
        #,Qt.WType_Dialog)
        self.setCaption(i18n("Create home directory"))
        self.updatingGUI = True

        toplayout = QVBoxLayout(self)
        toplayout.setSpacing(self.spacingHint())
        toplayout.setMargin(self.marginHint())

        contentbox = KHBox(self)
        contentbox.setSpacing(self.spacingHint())
        toplayout.addWidget(contentbox)
        toplayout.setStretchFactor(contentbox,1)

        label = QLabel(contentbox)
        #label.setPixmap(KGlobal.iconLoader().loadIcon("messagebox_warning", KIcon.NoGroup, KIcon.SizeMedium,
            #KIcon.DefaultState, None, True))   # TODO
        contentbox.setStretchFactor(label,0)

        textbox = KVBox(contentbox)

        textbox.setSpacing(self.spacingHint())
        textbox.setMargin(self.marginHint())

        # "%dir was selected as the home directory for %user. This directory already exists. Shall I:."
        self.toplabel = QLabel("",textbox)
        textbox.setStretchFactor(self.toplabel,0)

        self.radiogroup = QButtonGroup()
        #self.radiogroup.setRadioButtonExclusive(True)  # TODO

        # Use Existing home directory radio button.
        self.usehomedirectoryradio = QRadioButton(i18n("Use the existing directory without changing it."),textbox)
        textbox.setStretchFactor(self.usehomedirectoryradio,0)

        # Replace home directory radio button
        self.replacehomedirectoryradio = QRadioButton(i18n("Delete the directory and replace it with a new home directory."),textbox)
        textbox.setStretchFactor(self.replacehomedirectoryradio ,0)

        self.radiogroup.addButton(self.usehomedirectoryradio,0)
        self.radiogroup.addButton(self.replacehomedirectoryradio,1)

        # Buttons
        buttonbox = KHBox(self)
        toplayout.addWidget(buttonbox)

        buttonbox.setSpacing(self.spacingHint())
        toplayout.setStretchFactor(buttonbox,0)

        spacer = QWidget(buttonbox)
        buttonbox.setStretchFactor(spacer,1)

        okbutton = QPushButton(i18n("OK"),buttonbox)
        buttonbox.setStretchFactor(okbutton,0)
        self.connect(okbutton,SIGNAL("clicked()"),self.slotOkClicked)

        cancelbutton = QPushButton(i18n("Cancel"),buttonbox)
        cancelbutton.setDefault(True)
        buttonbox.setStretchFactor(cancelbutton,0)
        self.connect(cancelbutton,SIGNAL("clicked()"),self.slotCancelClicked)

    def do(self,userobj):
        # Setup the 
        self.toplabel.setText(i18n("The directory '%1' was entered as the home directory for new user '%2'.\n This directory already exists.") \
            .arg(userobj.getHomeDirectory()).arg(userobj.getUsername()) )
        self.radiogroup.setButton(0)

        if self.exec_()==QDialog.Accepted:
            if self.radiogroup.selectedId()==0:
                return OverwriteHomeDirectoryDialog.OK_KEEP
            else:
                return OverwriteHomeDirectoryDialog.OK_REPLACE
        else:
            return OverwriteHomeDirectoryDialog.CANCEL

    def slotOkClicked(self):
        self.accept()

    def slotCancelClicked(self):
        self.reject()
        

###########################################################################

class UserDeleteDialog(KDialog):
    def __init__(self,parent,admincontext):
        KDialog.__init__(self,parent)
        self.setModal(True)#,Qt.WType_Dialog)
        self.setCaption(i18n("Delete User Account"))
        self.admincontext = admincontext
        self.updatingGUI = True

        toplayout = QVBoxLayout(self)
        toplayout.setSpacing(self.spacingHint())
        toplayout.setMargin(self.marginHint())

        contentbox = KHBox(self)
        contentbox.setSpacing(self.spacingHint())
        toplayout.addWidget(contentbox)
        toplayout.setStretchFactor(contentbox,1)

        label = QLabel(contentbox)
        #label.setPixmap(KGlobal.iconLoader().loadIcon("messagebox_warning", KIcon.NoGroup, KIcon.SizeMedium,
            #KIcon.DefaultState, None, True)) # TODO
        contentbox.setStretchFactor(label,0)

        textbox = KVBox(contentbox)

        textbox.setSpacing(self.spacingHint())
        textbox.setMargin(self.marginHint())

        self.usernamelabel = QLabel("",textbox)
        textbox.setStretchFactor(self.usernamelabel,0)

        # Remove directory checkbox.
        self.deletedirectorycheckbox = QCheckBox(i18n("Delete home directory ()"),textbox)
        textbox.setStretchFactor(self.deletedirectorycheckbox,0)

        # Delete the User's private group.
        self.deletegroupcheckbox = QCheckBox(i18n("Delete group ()"),textbox)
        textbox.setStretchFactor(self.deletegroupcheckbox ,0)

        # Buttons
        buttonbox = KHBox(self)
        toplayout.addWidget(buttonbox)

        buttonbox.setSpacing(self.spacingHint())
        toplayout.setStretchFactor(buttonbox,0)

        spacer = QWidget(buttonbox)
        buttonbox.setStretchFactor(spacer,1)

        okbutton = QPushButton(i18n("OK"),buttonbox)
        buttonbox.setStretchFactor(okbutton,0)
        self.connect(okbutton,SIGNAL("clicked()"),self.slotOkClicked)

        cancelbutton = QPushButton(i18n("Cancel"),buttonbox)
        cancelbutton.setDefault(True)
        buttonbox.setStretchFactor(cancelbutton,0)
        self.connect(cancelbutton,SIGNAL("clicked()"),self.slotCancelClicked)

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

