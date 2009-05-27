#!/usr/bin/python
# -*- coding: utf-8 -*-
###########################################################################
# user.py - configuration for users for userconfig                        #
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

import os.path

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
from util.groups import PrivilegeNames


class UserModel(QAbstractItemModel):
    def __init__(self, parent, admincontext):
        QAbstractItemModel.__init__(self, parent)
        self.users = admincontext.getUsers()
        #print self.setHeaderData(0, Qt.Horizontal, QVariant(i18n("Real Name")), Qt.DisplayRole )
        #self.setHeaderData(1, Qt.Horizontal, QVariant(i18n("Username")) )

    def index(self, row, column, parent):
        return self.createIndex(row, column)
    
    def parent(self, index):
        return QModelIndex()
    
    def rowCount(self, parent):
        return len(self.users)
    
    def columnCount(self, parent):
        return 2
    
    def data(self, idx, role):
        if not idx.isValid():
            return QVariant()
            
        if role == Qt.DisplayRole:
            userobj = self.users[idx.row()]
            col = idx.column()
            if col == 0:
                return QVariant(userobj.getRealName())
            elif col == 1:
                return QVariant(userobj.getUsername())
        elif role == Qt.EditRole:
            userobj = self.users[idx.row()]
            return QVariant(userobj.getUID())
        else:
            return QVariant()
            
    def headerData(self, section, orientation, role):
        #col = section
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 0:
                return QVariant(i18n("Real Name"))
            elif section == 1:
                return QVariant(i18n("Username"))
        
        return QVariant()
    
    def hasChildren(self, parent):
        if parent.row() >= 0:
            return False
        else:
            return True


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
        #KDialogBase.__init__(self,KJanusWidget.Tabbed,i18n("User Account"),KDialogBase.Ok|KDialogBase.Cancel,
            #KDialogBase.Cancel,parent)
        KPageDialog.__init__( self, parent )
        if os.path.exists('ui/userproperties.ui'): 
            self.up = uic.loadUi('ui/userproperties.ui', self)
        #self.setObjectName( name )
        self.up.setModal( True )


        self.admincontext = admincontext
        self.updatingGUI = True


        self.enabledradiogroup = QButtonGroup()
        #self.enabledradiogroup.setRadioButtonExclusive(True)
        #self.up.statusLabel.setPixmap(KIcon("user-identity")) #TODO need to learn to do it right!

        #self.up.statusLabel.setPixmap(KIcon("encrypted")) #TODO need to learn to do it right!

        self.enabledradiogroup.addButton(self.up.enabledradio,0)
        self.enabledradiogroup.addButton(self.up.disabledradio,1)

        self.up.loginnameedit.setValidator(LoginNameValidator(self.up.loginnameedit))

        self.connect(self.up.loginnameedit, SIGNAL("textChanged(const QString &)"), self.slotLoginChanged)

        self.up.realnameedit.setValidator(RealUserNameValidator(self.up.realnameedit))

        self.up.uidedit.setValidator(QIntValidator(0,65535,self.up.tab))

        self.primarygroupedit = KComboBox(self.tab)
        self.gridLayout.addWidget(self.primarygroupedit, 5, 1, 1, 2)


        self.connect(self.up.homediredit, SIGNAL("textChanged(const QString &)"), self.slotHomeDirChanged)
        self.connect(self.up.homedirbutton,SIGNAL("clicked()"),self.slotBrowseHomeDirClicked)

        self.shelledit = KComboBox(True, self)
        self.up.gridLayout.addWidget(self.shelledit, 7, 1, 1, 2)
        for shell in self.admincontext.getUserShells():
            self.up.shelledit.addItem(shell)

        # Rudd-O rules.  Not so much, but enough to rule.
        # yeah it's not my finest hour, but it works like a charm over here.  Please feel free to clean up dead code that I commented
        # I extend my deepest thanks to the people that have worked hard to construct this tool in the first place.  I have no idea who the authors and contributors are, but it would make sense to have all the contributors listed on top of the file.
        # Privileges and groups tab

        #FIXME Need internationalized tab names
        #item.setHeader( i18n( "Privileges and groups" ) )
    
        # Password and Security Tab.
        # item.setHeader( i18n("Password && Security" )) #FIXME Need internationalization!


        #FIXME Doesn't work
        #self.up.passwordLabel.setPixmap(UserIcon("hi32-password"))


        self.validradiogroup = QButtonGroup()
        #self.validradiogroup.setRadioButtonExclusive(True) # TODO


        self.expiredate = KDateWidget(self.widget)
        self.gridLayout_3.addWidget(self.expiredate, 3, 2, 1, 1)

        self.validradiogroup.addButton(self.up.validalwaysradio,0)
        self.validradiogroup.addButton(self.up.expireradio,1)
        self.connect(self.validradiogroup,SIGNAL("clicked(int)"),self.slotValidUntilClicked)

        # Password Aging & Expiration.

        # [*] Require new password after: [_____5 days]
        self.connect(self.up.forcepasswordchangecheckbox,SIGNAL("toggled(bool)"),self.slotForcePasswordChangeToggled)

        self.up.warningedit.setSpecialValueText(i18n("Never"))

        self.up.disableexpireedit.setSpecialValueText(i18n("Never"))

        self.connect(self.up.enforcepasswordminagecheckbox,SIGNAL("toggled(bool)"),self.slotEnforePasswordAgeToggled)


        self.homedirdialog = KDirSelectDialog(KUrl.fromPath("/"),True,self)
        self.createhomedirectorydialog = OverwriteHomeDirectoryDialog(None)
        self.updatingGUI = False

    def _repopulateGroupsPrivileges(self,excludegroups=None):
        # needs listviews to be constructed.  Expects a list of PwdGroups to be excluded
        
        # rehash everything
        self.up.privilegeslistview.clear()
        self.up.groupslistview.clear()
        self.secondarygroupcheckboxes = {}
        pn = PrivilegeNames()
        
        if excludegroups: excludegroups = [ g.getGroupname() for g in excludegroups ]
        else: excludegroups = []
        for group in [g.getGroupname() for g in self.admincontext.getGroups()]:
            if group in excludegroups: continue
            if group in pn:
                name = i18n(unicode(pn[group]).encode(locale.getpreferredencoding()))
                wid = self.up.privilegeslistview
            else:
                name = unicode(group).encode(locale.getpreferredencoding())
                wid = self.up.groupslistview
            self.secondarygroupcheckboxes[group] = QListWidgetItem(name, wid)

    ########################################################################
    def showEditUser(self,userid):
        self.updatingGUI = True
        self.newusermode = False
        self.userobj = self.admincontext.lookupUID(userid)
        self.userid = userid
        self.up.passwordedit.clear()
        self.selectedgroups = [g.getGroupname() for g in self.userobj.getGroups()
            if g is not self.userobj.getPrimaryGroup()]
        
        # Rudd-O: now here we tick the appropriate group listing checkbox, and hide the currently active primary group of the user.  We are repopulating because if the user to edit changes, we need to hide the user's secondary group.  FIXME we should repopulate the groups privileges list when the primary group is changed in the other tab -- that is, on the change slot of the primary group drop down.
        self._repopulateGroupsPrivileges(excludegroups=[self.userobj.getPrimaryGroup()])
        for group,checkbox in self.secondarygroupcheckboxes.items():
            if group in self.selectedgroups: checkbox.setCheckState(Qt.Checked)
            else: checkbox.setCheckState(Qt.Unchecked)
        
        self.originalgroups = self.selectedgroups[:]
        self.selectedgroups.sort()
        self.__syncGUI()
        self.uidedit.setReadOnly(True)
        self.updatingGUI = False
        self.homedirectoryislinked = False
        if self.exec_()==QDialog.Accepted:
            self.__updateObjectFromGUI(self.userobj)
            # Set the password.
            if self.up.passwordedit.text()!="":
                self.userobj.setPassword(str(self.up.passwordedit.text()))
            # Update the groups for this user object. Rudd-O here's when you go in, stud.
            # we collect the selected groups
            self.selectedgroups = [ group for group,checkbox in self.secondarygroupcheckboxes.items() if checkbox.checkState() == Qt.Checked ]

            for g in self.userobj.getGroups(): # this seems wasteful to remove the user from all groups then re-add, why not a cross check?
                self.userobj.removeFromGroup(g)
            for gn in self.selectedgroups:
                self.userobj.addToGroup(self.admincontext.lookupGroupname(gn))

            primarygroupname = unicode(self.up.primarygroupedit.currentText())
            self.userobj.setPrimaryGroup(self.admincontext.lookupGroupname(primarygroupname))

            # Enable/Disable the account            
            self.userobj.setLocked(self.enabledradiogroup.checkedId() != 0)
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
            if group in self.selectedgroups: checkbox.setCheckState(Qt.Checked)
            else: checkbox.setCheckState(Qt.Checked)
        
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
        self.passwordedit.clear()
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
            # TODO not sure how to fix next line
            # self.selectedgroups = [ group for group.checkbox in self.secondarygroupcheckboxes.items() if checkbox.isOn() ]
            for gn in self.selectedgroups:
                self.userobj.addToGroup(self.admincontext.lookupGroupname(gn))

            # Set the password.
            # if self.passwordedit.password()!="":
            if self.passwordedit.text()!="":
                 self.userobj.setPassword(str(self.passwordedit.text()))

            # Enable/Disable the account            
            #self.userobj.setLocked(self.enabledradiogroup.id(self.enabledradiogroup.selected())!=0)
            self.userobj.setLocked(self.enabledradiogroup.id(self.enabledradiogroup.checkedButton())!=0)
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
            newusername = unicode(self.up.realnameedit.text())
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
                    self.up.homediredit.setText(homedir)
                self.updatingGUI = False

    ########################################################################
    def slotHomeDirChanged(self,text):
        if self.updatingGUI==False:
            self.homedirectoryislinked = False

    ########################################################################
    def __syncGUI(self):
        if self.userobj.isLocked():
            self.up.enabledradiogroup.button(1).setChecked(True)
        else:
            self.up.enabledradiogroup.button(0).setChecked(True)

        self.up.loginnameedit.setText(self.userobj.getUsername())
        self.up.realnameedit.setText(self.userobj.getRealName())
        self.up.uidedit.setText(unicode(self.userobj.getUID()))
        self.up.homediredit.setText(self.userobj.getHomeDirectory())
        self.up.shelledit.setEditText(self.userobj.getLoginShell())

        # Primary Group
        self.up.primarygroupedit.clear()
        allgroups = [g.getGroupname() for g in self.admincontext.getGroups()]
        allgroups.sort()
        self.availablegroups = allgroups[:]

        try:
            self.availablegroups.remove(self.userobj.getPrimaryGroup().getGroupname())
        except ValueError:
            pass

        if self.newusermode:
            # New user mode
            self.newprimarygroupname = \
                self.__fudgeNewGroupName(unicode(self.userobj.getUsername()))
            primarygroupname = self.newprimarygroupname
            self.up.primarygroupedit.addItem(self.newprimarygroupname)
        else:
            # Existing user mode
            primarygroupname = self.userobj.getPrimaryGroup().getGroupname()
        for group in allgroups:
            self.up.primarygroupedit.addItem(group)
        self.up.primarygroupedit.setEditText(primarygroupname)

        # If ShadowExpire is turn off then we change the radio box.
        if self.userobj.getExpirationDate() is None:
            self.up.validradiogroup.button(0).setChecked(True)
            self.up.expiredate.setDisabled(True)
            self.up.expiredate.setDate(SptimeToQDate(99999L))
        else:
            self.up.validradiogroup.button(1).setChecked(True)
            self.up.expiredate.setDisabled(False)
            self.up.expiredate.setDate(SptimeToQDate(self.userobj.getExpirationDate()))

        if self.userobj.getMaximumPasswordAge() is None:
            # Password aging is turn off
            self.up.forcepasswordchangecheckbox.setChecked(False)
            d = True
        else:
            # Password aging is turn on
            self.up.forcepasswordchangecheckbox.setChecked(True)
            d = False
        self.up.warningedit.setDisabled(d)
        self.up.maximumpasswordedit.setDisabled(d)
        self.up.disableexpireedit.setDisabled(d)

        if self.userobj.getPasswordExpireWarning() is None:
            self.up.warningedit.setValue(0)
        else:
            self.up.warningedit.setValue(self.userobj.getPasswordExpireWarning())

        if self.userobj.getMaximumPasswordAge() is None:
            self.up.maximumpasswordedit.setValue(30)
        else:
            self.up.maximumpasswordedit.setValue(self.userobj.getMaximumPasswordAge())

        if self.userobj.getPasswordDisableAfterExpire() is None:
            self.up.disableexpireedit.setValue(0)
        else:
            self.up.disableexpireedit.setValue(self.userobj.getPasswordDisableAfterExpire())

        minage = self.userobj.getMinimumPasswordAgeBeforeChange()
        self.up.enforcepasswordminagecheckbox.setChecked(minage>0)
        self.up.minimumpasswordedit.setDisabled(minage<=0)
        if minage<=0:
            minage = 1
        self.up.minimumpasswordedit.setValue(minage)

        if self.userobj.getLastPasswordChange() in (None,0):
            self.up.lastchangelabel.setText('-');
        else:
            self.up.lastchangelabel.setText(KGlobal.locale().formatDate(SptimeToQDate(int(self.userobj.getLastPasswordChange()))))

    ########################################################################
    def __updateObjectFromGUI(self,userobj):
        username = unicode(self.up.loginnameedit.text())
        userobj.setUsername(username)
        userobj.setRealName(unicode(self.up.realnameedit.text()))

        userobj.setHomeDirectory(unicode(self.up.homediredit.text()))
        userobj.setLoginShell(unicode(self.up.shelledit.currentText()))
        self.primarygroupname = unicode(self.up.primarygroupedit.currentText())
        groupobj =  self.admincontext.lookupGroupname(self.primarygroupname)
        if groupobj is not None:
            userobj.setPrimaryGroup(groupobj)

        # Password expiration.
        if self.validradiogroup.id(self.validradiogroup.checkedButton())==0:
            # Password is always valid.
            userobj.setExpirationDate(None)
        else:
            # Password will expire at...
            userobj.setExpirationDate(QDateToSptime(self.expiredate.date()))

        if self.up.forcepasswordchangecheckbox.isChecked():
            userobj.setMaximumPasswordAge(self.maximumpasswordedit.value())
        else:
            userobj.setMaximumPasswordAge(None)

        if self.up.disableexpireedit.value()==0:
            userobj.setPasswordDisableAfterExpire(None)
        else:
            userobj.setPasswordDisableAfterExpire(self.disableexpireedit.value())

        if self.up.enforcepasswordminagecheckbox.isChecked():
            userobj.setMinimumPasswordAgeBeforeChange(self.minimumpasswordedit.value())
        else:
            userobj.setMinimumPasswordAgeBeforeChange(0)

        userobj.setPasswordExpireWarning(self.warningedit.value())

    ########################################################################
    def slotBrowseHomeDirClicked(self):
        fileurl = KUrl()
        fileurl.setPath(self.homediredit.text())
        self.homedirdialog.setCurrentUrl(fileurl)
        if self.homedirdialog.exec_()==QDialog.Accepted:
            self.up.homediredit.setText(self.homedirdialog.url().path())
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
        self.up.warningedit.setDisabled(on)
        self.up.maximumpasswordedit.setDisabled(on)
        self.up.disableexpireedit.setDisabled(on)

    ########################################################################
    def slotEnforePasswordAgeToggled(self,on):
        self.up.minimumpasswordedit.setDisabled(not on)

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

