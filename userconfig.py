#!/usr/bin/python
# -*- coding: utf-8 -*-

#############################################################################
##
## Copyright 2003-2006 Simon Edwards <simon@simonzone.com>
## Copyright 2008-2009 Yuriy Kozlov <yuriy-kozlov@kubuntu.org>
## Copyright 2008-2009 Jonathan Thomas <echidnaman@kubuntu.org>,
## Copyright 2008-2009 Ralph Janke <txwikinger@ubuntu.com>
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


# Python imports
import sys
import os.path
from os.path import join as pj

# Qt imports
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4 import uic

# KDE imports
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *

# Userconfig imports
from authdb.util import getContext
from user_dialogs import UserEditDialog, UserDeleteDialog
from models import UserModel, GroupModel, FilterSystemAcctsProxyModel, \
    GroupListModel, SimpleGroupListProxyModel
from group_dialogs import GroupEditDialog

def translate(self, prop):
    """reimplement method from uic to change it to use gettext"""
    if prop.get("notr", None) == "true":
        return self._cstring(prop)
    else:
        if prop.text is None:
            return ""
        text = prop.text.encode("UTF-8")
        return i18n(text)

uic.properties.Properties._string = translate

programname = "userconfig"
version = "0.9.0"
# Are we running as a separate standalone application or in KControl?
standalone = __name__=='__main__'

# Running as the root user or not?
isroot = os.getuid()==0

if os.path.exists("ui/users.ui"):
    APP_DIR = unicode(QDir.currentPath())
else:
    f = KGlobal.dirs().findResourceDir("data", "userconfig/ui/users.ui")
    APP_DIR = pj(unicode(f), 'userconfig/')
UI_DIR = pj(APP_DIR, 'ui/')

###########################################################################
# Try translating this code to C++. I dare ya!
if standalone:
    programbase = KPageDialog
else:
    programbase = KCModule

class UserConfigApp(programbase):
    def __init__(self, component_data=None, parent=None):
        global standalone, isroot
        KGlobal.locale().insertCatalog("userconfig")

        self.aboutdata = MakeAboutData()
        
        if standalone:
            KPageDialog.__init__(self)
            self.setFaceType(KPageDialog.Tabbed)
            
            # Set up buttons
            self.setButtons(KDialog.ButtonCode(KDialog.Close | KDialog.User1))
            self.setButtonText(KDialog.ButtonCode(KDialog.User1), i18n("About"))
            self.setButtonIcon(KDialog.User1, KIcon('help-about'))
            self.connect(self, SIGNAL("user1Clicked()"), self.slotUser1)
            
            self.aboutus = KAboutApplicationDialog(self.aboutdata, self)
            # Make UI set up code the same for standalone
            tabcontrol = self
        else:
            KCModule.__init__(self, component_data, parent)
            self.setAboutData(self.aboutdata)
            self.setButtons(KCModule.Help)
            self.setUseRootOnlyMessage(True)
            
            # Create layout and tabs otherwise taken care of by KPageDialog
            toplayout = QVBoxLayout()
            self.setLayout(toplayout)
            tabcontrol = KPageWidget(self)
            tabcontrol.setFaceType(KPageWidget.Tabbed)
            toplayout.addWidget(tabcontrol)
        
        # Load UI
        self.userstab = uic.loadUi(pj(UI_DIR, 'users.ui'))
        userstab_pwi = tabcontrol.addPage(self.userstab, i18n("User Accounts") )
        self.groupstab = uic.loadUi(pj(UI_DIR, 'groups.ui'))
        groupstab_pwi = tabcontrol.addPage(self.groupstab, i18n("Groups") )

        # Create a configuration object.
        self.config = KConfig("userconfigrc")
        self.generalconfiggroup = KConfigGroup(self.config, "General")
        self.optionsconfiggroup = KConfigGroup(self.config, "Options")

        KIconLoader.global_().addAppDir("guidance")
        
        self.admincontext = getContext(isroot)

        self.selecteduserid = None
        self.selectedgroupid = None

        self.updatingGUI = True

        #######################################################################
        # Set up the users tab
        
        userstab_pwi.setIcon(KIcon('user-identity'))

        self.userlistmodel = UserModel(None, self.admincontext.getUsers())
        self.userstab.userlistview.setModel(self.userlistmodel)
        
        self.userlist_nosys_model = FilterSystemAcctsProxyModel(None)
        self.userlist_nosys_model.setSourceModel(self.userlistmodel)
        
        # Last column is really big without this
        #fix_treeview(self.userstab.userlistview)
        self.userstab.userlistview.setColumnWidth(2, 20)
        
        self.connect( self.userstab.userlistview.selectionModel(),
                      SIGNAL("currentChanged(const QModelIndex&,const QModelIndex&)"),
                      self.slotUserSelected )
        
        self.secondary_groups_model = GroupListModel(None, [], None)
        simple_sec_groups_model = SimpleGroupListProxyModel(None)
        simple_sec_groups_model.setSourceModel(self.secondary_groups_model)
        self.userstab.secondarygroupslist.setModel(simple_sec_groups_model)
        
        if isroot:
            self.connect( self.userstab.userlistview,
                          SIGNAL("doubleClicked(const QModelIndex&)"),
                          self.slotModifyClicked )
        
        # TODO: context menu
        #self.connect(self.userstab.userlistview, SIGNAL("contextMenu(KListView*,QListViewItem*,const QPoint&)"), self.slotUserContext)

        self.connect( self.userstab.show_sysusers_checkbox,
                      SIGNAL("toggled(bool)"),
                      self.slotShowSystemUsers )
        
        # Buttons
        self.connect( self.userstab.modifybutton,
                      SIGNAL("clicked()"),
                      self.slotModifyClicked )
        self.userstab.modifybutton.setIcon( SmallIconSet('user-properties') )

        self.connect( self.userstab.newbutton,
                      SIGNAL("clicked()"),
                      self.slotNewClicked )
        self.userstab.newbutton.setIcon( SmallIconSet('list-add-user') )

        self.connect( self.userstab.deletebutton,
                      SIGNAL("clicked()"),
                      self.slotDeleteClicked)
        self.userstab.deletebutton.setIcon( SmallIconSet('list-remove-user') )

        self.userstab.statusiconlabel.setPixmap(
            KIconLoader.global_().loadIcon('object-locked', KIconLoader.Small))
        self.__selectUser(None)

        #######################################################################
        # Set up the groups tab

        #FIXME: Need to find Oxygen group icon
        groupstab_pwi.setIcon(KIcon('user-group-properties'))

        self.grouplistmodel = GroupModel(None, self.admincontext.getGroups())
        self.groupstab.grouplistview.setModel(self.grouplistmodel)
        
        self.grouplist_nosys_model = FilterSystemAcctsProxyModel(None)
        self.grouplist_nosys_model.setSourceModel(self.grouplistmodel)
        
        # Last column is really big without this
        fix_treeview(self.groupstab.grouplistview)
        
        self.groupmemberslistmodel = UserModel(None, [])
        self.groupstab.groupmemberlistview.setModel(
                                                self.groupmemberslistmodel )
        # Last column is really big without this
        fix_treeview(self.groupstab.groupmemberlistview)
            
        self.connect( self.groupstab.grouplistview.selectionModel(),
                      SIGNAL("currentChanged(const QModelIndex&,const QModelIndex&)"),
                      self.slotGroupSelected )
        
        if isroot:
            self.connect( self.groupstab.grouplistview,
                          SIGNAL("doubleClicked(const QModelIndex&)"),
                          self.slotModifyGroupClicked )

        # TODO: group context menu
        #self.connect(self.grouplist, SIGNAL("contextMenu(KListView*,QListViewItem*,const QPoint&)"), 
                #self.slotGroupContext)

        self.connect( self.groupstab.show_sysgroups_checkbox,
                      SIGNAL("toggled(bool)"),
                      self.slotShowSystemGroups )

        # Buttons
        self.connect( self.groupstab.modifygroupbutton,
                      SIGNAL("clicked()"),
                      self.slotModifyGroupClicked )
        self.groupstab.modifygroupbutton.setIcon(
                                        SmallIconSet('user-group-properties') )

        self.connect( self.groupstab.newgroupbutton,
                      SIGNAL("clicked()"),
                      self.slotNewGroupClicked )
        self.groupstab.newgroupbutton.setIcon( SmallIconSet('user-group-new') )

        self.connect( self.groupstab.deletegroupbutton,
                      SIGNAL("clicked()"),
                      self.slotDeleteGroupClicked )
        self.groupstab.deletegroupbutton.setIcon(
                                        SmallIconSet('user-group-delete') )

        # Disable some buttons.  Disable all if not root.
        disablebuttons = [ self.userstab.modifybutton,
                           self.groupstab.modifygroupbutton,
                           self.userstab.deletebutton,
                           self.groupstab.deletegroupbutton,
                           ]
        if not isroot:
            disablebuttons += ( self.userstab.newbutton,
                                self.groupstab.newgroupbutton )
        for widget in disablebuttons:
            widget.setDisabled(True)

        self.usereditdialog = UserEditDialog(None,self.admincontext)
        self.userdeletedialog = UserDeleteDialog(None,self.admincontext)
        self.groupeditdialog = GroupEditDialog(None,self.admincontext)
        
        # exec_ doesn't get called for a KCM
        if not standalone:
            self.__loadOptions()

    #######################################################################
    def exec_(self):
        global programbase
        self.__loadOptions()
        programbase.exec_(self)
        self.__saveOptions()

    #######################################################################
    def slotUser1(self):
        self.aboutus.show()

    #######################################################################
    def slotUserContext(self,l,v,p):
        cmenu = KPopupMenu(self,"MyActions")
        cmenu.insertItem(i18n("Modify..."), self.slotModifyClicked, 0, 0)
        cmenu.insertItem(i18n("Delete..."), self.slotDeleteClicked, 0, 1)
        if not isroot:
            cmenu.setItemEnabled(0,False)
            cmenu.setItemEnabled(1,False)

        cmenu.exec_(p)

    #######################################################################
    def slotGroupContext(self,l,v,p):
        cmenu = KPopupMenu(self,"MyActions")
        cmenu.insertItem(i18n("Modify..."), self.slotModifyGroupClicked, 0, 0)
        cmenu.insertItem(i18n("Delete..."), self.slotDeleteGroupClicked, 0, 1)
        if not isroot:
            cmenu.setItemEnabled(0,False)
            cmenu.setItemEnabled(1,False)
        cmenu.exec_(p)

    #######################################################################
    def slotUserSelected(self, current):
        """ Qt SLOT used when a user is clicked on in the list """
        userid = current.data(Qt.EditRole).toInt()[0]
        self.updatingGUI = True
        self.__selectUser(userid)
        self.updatingGUI = False

    #######################################################################
    def slotModifyClicked(self):
        self.usereditdialog.showEditUser(self.selecteduserid)
        self.updatingGUI = True
        self.__updateUser(self.selecteduserid)
        self.grouplistmodel.setItems(self.admincontext.getGroups())
        self.__selectUser(self.selecteduserid)
        self.updatingGUI = False

    #######################################################################
    def slotNewClicked(self):
        newuid = self.usereditdialog.showNewUser()
        if newuid != None:
            self.updatingGUI = True
            self.userlistmodel.setItems(self.admincontext.getUsers())
            self.grouplistmodel.setItems(self.admincontext.getGroups())
            self.__selectUserInList(newuid)
            self.__selectUser(newuid)
            self.updatingGUI = False

    #######################################################################
    def slotDeleteClicked(self):
        if self.userdeletedialog.do(self.selecteduserid):
            self.updatingGUI = True
            self.userlistmodel.setItems(self.admincontext.getUsers())
            self.grouplistmodel.setItems(self.admincontext.getGroups())
            self.selecteduserid = None
            self.__selectUser(self.selecteduserid)
            self.updatingGUI = False

    #######################################################################
    def slotGroupSelected(self, current):
        groupid = current.data(Qt.EditRole).toInt()[0]
        self.updatingGUI = True
        self.__selectGroup(groupid)
        self.updatingGUI = False

    #######################################################################
    def slotShowSystemUsers(self, on):
        if on:
            self.userstab.userlistview.setModel(self.userlistmodel)
        else:
            self.userstab.userlistview.setModel(self.userlist_nosys_model)
        self.connect( self.userstab.userlistview.selectionModel(),
                      SIGNAL("currentChanged(const QModelIndex&,const QModelIndex&)"),
                      self.slotUserSelected )
        
    #######################################################################
    def slotShowSystemGroups(self, on):
        if on:
            self.groupstab.grouplistview.setModel(self.grouplistmodel)
        else:
            self.groupstab.grouplistview.setModel(self.grouplist_nosys_model)
        self.connect( self.groupstab.grouplistview.selectionModel(),
                      SIGNAL("currentChanged(const QModelIndex&,const QModelIndex&)"),
                      self.slotGroupSelected )

    #######################################################################
    def slotModifyGroupClicked(self):
        if self.groupeditdialog.showEditGroup(self.selectedgroupid) is not None:
            self.updatingGUI = True
            self.__updateGroup(self.selectedgroupid)
            self.__selectGroup(self.selectedgroupid)
            self.__updateUser(self.selecteduserid)
            self.__selectUser(self.selecteduserid)
            self.updatingGUI = False

    #######################################################################
    def slotNewGroupClicked(self):
        newgroupid = self.groupeditdialog.showNewGroup()
        if newgroupid is not None:
            self.updatingGUI = True
            self.grouplistmodel.setItems(self.admincontext.getGroups())
            self.__selectGroupInList(newgroupid)
            self.__selectGroup(newgroupid)
            if self.selecteduserid is not None:
                self.__updateUser(self.selecteduserid)
                self.__selectUser(self.selecteduserid)
            self.updatingGUI = False

    #######################################################################
    def slotDeleteGroupClicked(self):
        if self.selectedgroupid is not None:
            groupobj = self.admincontext.lookupGID(self.selectedgroupid)
            groupname = groupobj.getGroupname()
            gid = groupobj.getGID()
            nummembers = len(groupobj.getUsers())

            message = i18n("Are you sure you want to delete group '%1' (%2)?" +
                           "\nIt currently has %3 members.")\
                           .arg(groupname).arg(gid).arg(nummembers)
            if KMessageBox.warningYesNo(self, message,
                                i18n("Delete Group?")) == KMessageBox.Yes:
                self.admincontext.removeGroup(groupobj)
                self.admincontext.save()
                
                self.updatingGUI = True
                self.grouplistmodel.setItems(self.admincontext.getGroups())
                self.selectedgroupid = None
                self.__selectGroup(self.selectedgroupid)
                if self.selecteduserid is not None:
                    self.__updateUser(self.selecteduserid)
                    self.__selectUser(self.selecteduserid)
                self.updatingGUI = False

    #######################################################################
    def __updateUser(self, userid):
        """ Lets the user list view know the user data changed """
        idx = self.userlistmodel.indexFromID(userid)
        self.userlistmodel.emit(
                    SIGNAL("dataChanged(QModelIndex&,QModelIndex&)"), idx, idx)

    #######################################################################
    def __updateGroup(self, groupid):
        """ Lets the group list view know the group data changed """
        idx = self.grouplistmodel.indexFromID(groupid)
        self.grouplistmodel.emit(
                    SIGNAL("dataChanged(QModelIndex&,QModelIndex&)"), idx, idx)

    #######################################################################
    def __selectUserInList(self, userid):
        """ Selects the user in the list view """
        selection = self.userlistmodel.selectionFromID(userid)
        if not self.userstab.show_sysusers_checkbox.isChecked():
            selection = self.userlist_nosys_model.mapSelectionFromSource(
                                                            selection)
        self.userstab.userlistview.selectionModel().select(
                selection, QItemSelectionModel.Select)

    #######################################################################
    def __selectUser(self, userid):
        """ Selects a user in the list and updates the GUI to reflect
            information about that user.  Enables/disables buttons as needed.
            
            Updates self.selecteduserid
        """
        self.selecteduserid = userid

        userobj = self.admincontext.lookupUID(userid)

        if userobj is None:
            self.userstab.userdetails_groupbox.hide();
            # Enable/disable buttons
            self.userstab.modifybutton.setEnabled(False)
            self.userstab.deletebutton.setEnabled(False)
            return
            
        self.userstab.loginname.setText(userobj.getUsername())
        self.userstab.userdetails_groupbox.setTitle(
            i18n("Details for %1", userobj.getDisplayName()))
        self.userstab.uid.setText(unicode(userid))
        if userobj.isLocked():
            self.userstab.statuslabel.show()
            self.userstab.statusiconlabel.show()
        else:
            self.userstab.statuslabel.hide()
            self.userstab.statusiconlabel.hide()

        # Primary Group
        primarygroupobj = userobj.getPrimaryGroup()
        primarygroupname = primarygroupobj.getGroupname()
        self.userstab.primarygroup.setText(primarygroupname)

        # Secondary Groups
        secondarygroups = [g for g in userobj.getGroups()
                                        if g is not userobj.getPrimaryGroup()]
        self.secondary_groups_model.setItems(secondarygroups)
        self.secondary_groups_model.setUser(userobj)
        
        if isroot:
            # Enable/disable buttons
            self.userstab.modifybutton.setEnabled(True)
            # Don't allow deletion the root account
            self.userstab.deletebutton.setDisabled(userobj.getUID() == 0)
        
        self.userstab.userdetails_groupbox.show()

    #######################################################################
    def __selectGroupInList(self, groupid):
        """ Selects the user in the list view """
        selection = self.grouplistmodel.selectionFromID(groupid)
        if not self.groupstab.show_sysgroups_checkbox.isChecked():
            selection = self.grouplist_nosys_model.mapSelectionFromSource(
                                                            selection)
        self.groupstab.grouplistview.selectionModel().select(
                selection, QItemSelectionModel.Select)

    #######################################################################
    def __selectGroup(self,groupid):
        """ Selects a user in the list and updates the GUI to reflect
            information about that user.  Enables/disables buttons as needed.
            
            Updates self.selectedgroupid
        """
        self.selectedgroupid = groupid

        groupobj = self.admincontext.lookupGID(groupid)
        
        if groupobj is None:
            self.groupmemberslistmodel.setItems([])
            # Enable/disable buttons
            self.groupstab.modifygroupbutton.setEnabled(False)
            self.groupstab.deletegroupbutton.setEnabled(False)
            return
        
        members = groupobj.getUsers()
        self.groupmemberslistmodel.setItems(members)
        
        if isroot:
            # Enable/disable buttons
            self.groupstab.modifygroupbutton.setEnabled(True)
            # Don't allow deletion of the root group
            self.groupstab.deletegroupbutton.setDisabled(groupobj.getGID()==0)

    #######################################################################
    def __loadOptions(self):
        global standalone
        if standalone:
            self.restoreDialogSize(self.generalconfiggroup)
        
        showsystemusers = self.optionsconfiggroup.readEntry("ShowSystemUsers")
        if showsystemusers:
            showsystemusers = int(showsystemusers)
        showsystemusers = bool(showsystemusers)
        self.userstab.show_sysusers_checkbox.setChecked(showsystemusers)
        # The signal-slot connection doesn't seem to work here.. before exec?
        self.slotShowSystemUsers(showsystemusers)
        
        showsystemgroups = self.optionsconfiggroup.readEntry("ShowSystemGroups")
        if showsystemgroups:
            showsystemgroups = int(showsystemgroups)
        showsystemgroups = bool(showsystemgroups)
        self.groupstab.show_sysgroups_checkbox.setChecked(showsystemgroups)
        # The signal-slot connection doesn't seem to work here.. before exec?
        self.slotShowSystemGroups(showsystemgroups)

    #######################################################################
    def __saveOptions(self):
        global isroot
        if isroot:
            return
        self.saveDialogSize(self.generalconfiggroup)
        
        self.optionsconfiggroup.writeEntry("ShowSystemUsers",
                str(int(self.userstab.show_sysusers_checkbox.isChecked())))
        self.optionsconfiggroup.writeEntry("ShowSystemGroups",
                str(int(self.groupstab.show_sysgroups_checkbox.isChecked())))
        self.config.sync()

###########################################################################


def fix_treeview(view):
    """ Resizes all columns to contents """
    for col in range(view.model().columnCount()):
        view.resizeColumnToContents(col)

##########################################################################
def MakeAboutData():
    aboutdata = KAboutData("userconfig", "userconfig", ki18n(programname), version,
        ki18n("User and Group Configuration Tool"),
        KAboutData.License_GPL,
        ki18n("Copyright (C) 2003-2007 Simon Edwards\n" +
              "Copyright (C) 2008-2009 by Yuriy Kozlov, Jonathan Thomas, " +
              "Ralph Janke"))
    aboutdata.addAuthor(ki18n("Simon Edwards"), ki18n("Developer"), "simon@simonzone.com", "http://www.simonzone.com/software/")
    aboutdata.addAuthor(ki18n("Sebastian Kügler"), ki18n("Developer"), "sebas@kde.org", "http://vizZzion.org")
    aboutdata.addAuthor(ki18n("Yuriy Kozlov"), ki18n("Developer"), "yuriy-kozlov@kubuntu.org", "http://www.yktech.us")
    aboutdata.addAuthor(ki18n("Jonathan Thomas"), ki18n("Developer"), "", "")
    aboutdata.addAuthor(ki18n("Ralph Janke"), ki18n("Developer"), "", "")
    return aboutdata

if standalone:
    aboutdata = MakeAboutData()

    KCmdLineArgs.init(sys.argv, aboutdata)

    kapp = KApplication()
    userconfigapp = UserConfigApp()
    userconfigapp.exec_()

def CreatePlugin(widget_parent, parent, component_data):
    return UserConfigApp(component_data, widget_parent)
