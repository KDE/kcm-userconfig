#!/usr/bin/python
# -*- coding: utf-8 -*-
###########################################################################
# userconfig.py - main program for userconfig control module              #
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

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4 import uic
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.kio import *
import sys
import os.path
import shutil
from util import unixauthdb
from util.groups import PrivilegeNames
from user import UserEditDialog, UserDeleteDialog
from models import UserModel, GroupModel, FilterSystemAcctsProxyModel
from group import GroupEditDialog
import locale

programname = "userconfig"
version = "0.9.0"
# Are we running as a separate standalone application or in KControl?
standalone = __name__=='__main__'

# Running as the root user or not?
isroot = os.getuid()==0
#isroot = True



###########################################################################
# Try translating this code to C++. I dare ya!
if standalone:
    programbase = KPageDialog
else:
    programbase = KCModule

class UserConfigApp(programbase):
    def __init__(self,parent=None,name=None):
        global standalone,isroot
        KGlobal.locale().insertCatalog("guidance")

        self.aboutdata = MakeAboutData()
        
        if standalone:
            KPageDialog.__init__(self)
            self.setFaceType(KPageDialog.Tabbed)
            
            # Set up buttons
            self.setButtons(KDialog.ButtonCode(KDialog.Close | KDialog.User1))
            self.setButtonText(KDialog.ButtonCode(KDialog.User1), i18n("About"))
            self.setButtonIcon(KDialog.User1, KIcon('help-about'))
            self.connect(self, SIGNAL("user1Clicked()"), self.slotUser1)
            
            # Load UI
            #if os.path.exists('ui/maindialog.ui'):
            self.userstab = uic.loadUi('ui/users.ui')
            self.addPage(self.userstab, i18n("Users") )
            self.groupstab = uic.loadUi('ui/groups.ui')
            self.addPage(self.groupstab, i18n("Groups") )
            #FIXME: SRSLY! Need to know where the ui crap'll be installed and
            #check for it there too.
        else:
            KCModule.__init__(self,parent,name)
            self.setButtons(0)
            self.aboutdata = MakeAboutData()
            
            # TODO!
            #toplayout = KVBoxLayout( self, 0, KDialog.spacingHint() )
            #tabcontrol = QTabWidget(self)
            #toplayout.addWidget(tabcontrol)
            #toplayout.setStretchFactor(tabcontrol,1)

        # Create a configuration object.
        self.config = KConfig("userconfigrc")
        self.generalconfiggroup = KConfigGroup(self.config, "General")
        self.optionsconfiggroup = KConfigGroup(self.config, "Options")

        KIconLoader.global_().addAppDir("guidance")
        
        self.admincontext = unixauthdb.getContext(isroot)

        self.selecteduserid = None
        self.selectedgroupid = None

        self.updatingGUI = True
        
        self.aboutus = KAboutApplicationDialog(self.aboutdata, self)

        #######################################################################
        # Set up the users tab

        self.userstab.accountIconLabel.setPixmap(
            KIconLoader.global_().loadIcon('user-identity', KIconLoader.Small))

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

        userdetails_groupbox = self.userstab.userdetails_groupbox

        # FIXME need to implement w/ ui file when we can
        #if not standalone:
            #tabcontrol.addTab(vbox,i18n("Users"))

        ##--- Groups Tab ---
        #if standalone:
            #groupsvbox = KVBox(self)
            #item = self.addPage( groupsvbox, i18n( "Groups" ) )
            #item.setHeader( i18n( "Groups" ) )
            #hb = KHBox(groupsvbox)
        #else:
            #groupsvbox = KVBox(tabcontrol)
            #groupsvbox.setMargin(KDialog.marginHint())
            #hb = KHBox(groupsvbox)

        #######################################################################
        # Set up the groups tab

        #FIXME: Need to find Oxygen group icon
        self.groupstab.groupIconLabel.setPixmap(
            KIconLoader.global_()\
                .loadIcon('user-group-properties', KIconLoader.Small))

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


        #FIXME Need to handle non-standalone when it can be non-standalone
        #if not standalone:
            #tabcontrol.addTab(groupsvbox,i18n("Groups"))
        

        self.usereditdialog = UserEditDialog(None,self.admincontext)
        self.userdeletedialog = UserDeleteDialog(None,self.admincontext)
        self.groupeditdialog = GroupEditDialog(None,self.admincontext)

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
    def sizeHint(self):
        global programbase
        size_hint = programbase.sizeHint(self)
        # Just make the dialog a little shorter by default.
        size_hint.setHeight(size_hint.height()-150) 
        return size_hint

    #######################################################################
    def slotCloseButton(self):
        self.close()

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
        self.__selectUser(self.selecteduserid)
        self.updatingGUI = False

    #######################################################################
    def slotNewClicked(self):
        newuid = self.usereditdialog.showNewUser()
        if newuid != None:
            self.updatingGUI = True
            self.userlistmodel.setItems(self.admincontext.getUsers())
            self.__selectUserInList(newuid)
            #self.userstab.userlistview.repaint()
            self.__selectUser(newuid)
            self.updatingGUI = False

    #######################################################################
    def slotDeleteClicked(self):
        if self.userdeletedialog.deleteUser(self.selecteduserid):
            self.updatingGUI = True
            self.userlistmodel.setItems(self.admincontext.getUsers())
            #self.userstab.userlistview.repaint()
            self.selecteduserid = None
            #self.__updateUserList()
            #self.__updateGroupList()
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
        if self.selectedgroupid!=None:
            if self.groupeditdialog.showEditGroup(self.selectedgroupid):
                #self.__selectGroup(self.selectedgroupid)
                self.updatingGUI = True
                self.__updateUser(self.selecteduserid)
                #self.__selectUser(self.selecteduserid)
                self.updatingGUI = False

    #######################################################################
    def slotNewGroupClicked(self):
        newgroupid = self.groupeditdialog.showNewGroup()
        if newgroupid!=None:
            self.updatingGUI = True
            #self.__updateGroupList()
            #self.__updateGroupList()
            self.__selectGroup(newgroupid)
            self.__updateUser(self.selecteduserid)
            #self.__selectUser(self.selecteduserid)
            self.updatingGUI = False

    #######################################################################
    def slotDeleteGroupClicked(self):
        if self.selectedgroupid!=None:
            groupobj = self.admincontext.lookupGID(self.selectedgroupid)
            groupname = groupobj.getGroupname()
            gid = groupobj.getGID()
            nummembers = len(groupobj.getUsers())

            message = i18n("Are you sure you want to delete group '%1' (%2)?\nIt currently has %3 members.").arg(groupname).arg(gid).arg(nummembers)
            if KMessageBox.warningYesNo(self,message,i18n("Delete Group?"))==KMessageBox.Yes:
                self.admincontext.removeGroup(groupobj)
                self.admincontext.save()
                self.updatingGUI = True
                #self.__updateGroupList()
                self.__updateUser(self.selecteduserid)
                self.__selectUser(self.selecteduserid)
                self.updatingGUI = False

    #######################################################################
    def __updateUser(self, userid):
        idx = self.userlistmodel.indexFromID(userid)
        self.userlistmodel.emit(
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

        self.userstab.loginname.setText(userobj.getUsername())
        self.userstab.realname.setText(userobj.getRealName())
        self.userstab.uid.setText(unicode(userid))
        if userobj.isLocked():
            self.userstab.status.setText(i18n("Disabled"))
        else:
            self.userstab.status.setText(i18n("Enabled"))

        # Primary Group
        primarygroupobj = userobj.getPrimaryGroup()
        primarygroupname = primarygroupobj.getGroupname()
        self.userstab.primarygroup.setText(primarygroupname)

        # Secondary Groups
        secondarygroups = [g.getGroupname() for g in userobj.getGroups()
                                        if g is not userobj.getPrimaryGroup()]
        self.userstab.secondarygroup.setText(
                                     unicode(i18n(", ")).join(secondarygroups))

        if isroot:
            # Enable/disable buttons
            self.userstab.modifybutton.setEnabled( True )
            # Don't allow deletion the root account
            self.userstab.deletebutton.setDisabled(userobj.getUID() == 0)

    #######################################################################
    def __selectGroup(self,groupid):
        """ Selects a user in the list and updates the GUI to reflect
            information about that user.  Enables/disables buttons as needed.
            
            Updates self.selectedgroupid
        """
        self.selectedgroupid = groupid

        groupobj = self.admincontext.lookupGID(groupid)
        members = groupobj.getUsers()
        self.groupmemberslistmodel.setItems( members )
        
        if isroot:
            # Enable/disable buttons
            self.groupstab.modifygroupbutton.setEnabled( True )
            # Don't allow deletion of the root group
            self.groupstab.deletegroupbutton.setDisabled(groupobj.getGID()==0)

    #######################################################################
    def __loadOptions(self):
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

    #######################################################################
    # KControl virtual void methods
    def load(self):
        pass
    def save(self):
        pass
    def defaults(self):
        pass        
    def sysdefaults(self):
        pass

    def aboutData(self):
        # Return the KAboutData object which we created during initialisation.
        return self.aboutdata
    def buttons(self):
        # Only supply a Help button. Other choices are Default and Apply.
        return KCModule.Help

###########################################################################






###########################################################################
#class ListPickerDialog(KDialog):
    #def __init__(self,parent,caption,leftlabel,rightlabel):
        ##KDialogBase.__init__(self,parent,None,True,caption,KDialogBase.Ok|KDialogBase.Cancel, KDialogBase.Cancel)
        #KDialog.__init__(parent)
        #KDialog.setCaption(caption)
        #KDialog.setModal(True)
        #KDialog.setButtons(KDialog.Ok|KDialog.Cancel)

        #self.tophbox = KHBox(self)
        #self.setMainWidget(self.tophbox)
        #self.tophbox.setSpacing(self.spacingHint())
        ## Available Groups
        #vbox = KVBox(self.tophbox)
        #self.tophbox.setStretchFactor(vbox,1)
        #label = QLabel(leftlabel,vbox)
        #vbox.setStretchFactor(label,0)
        #self.availablelist = KListBox(vbox)
        #vbox.setStretchFactor(self.availablelist,1)

        ## ->, <- Buttons
        #vbox = KVBox(self.tophbox)
        #self.tophbox.setStretchFactor(vbox,0)
        #spacer = QWidget(vbox);
        #vbox.setStretchFactor(spacer,1)
        #self.addbutton = KPushButton(i18n("Add ->"),vbox)
        #self.connect(self.addbutton,SIGNAL("clicked()"),self.slotAddClicked)
        #vbox.setStretchFactor(self.addbutton,0)
        #self.removebutton = KPushButton(i18n("<- Remove"),vbox)
        #self.connect(self.removebutton,SIGNAL("clicked()"),self.slotRemoveClicked)
        #vbox.setStretchFactor(self.removebutton,0)
        #spacer = QWidget(vbox);
        #vbox.setStretchFactor(spacer,1)

        ## Selected Groups
        #vbox = KVBox(self.tophbox)
        #self.tophbox.setStretchFactor(vbox,1)
        #label = QLabel(rightlabel,vbox)
        #vbox.setStretchFactor(label,0)
        #self.selectedlist = KListBox(vbox)
        #vbox.setStretchFactor(self.selectedlist,1)

    ########################################################################
    #def do(self,grouplist,selectedlist):
        #self.selectedlist.clear()
        #for item in selectedlist:
            #self.selectedlist.insertItem(item)
        #self.selectedlist.sort()

        #self.availablelist.clear()
        #for item in grouplist:
            #if item not in selectedlist:
                #self.availablelist.insertItem(item)
        #self.availablelist.sort()

        #self._selectFirstAvailable()
        #self.addbutton.setDisabled(self.availablelist.selectedItem()==None)

        #self._selectFirstSelected()
        #self.removebutton.setDisabled(self.selectedlist.selectedItem()==None)

        #if self.exec_()==QDialog.Accepted:
            #newlist = []
            #for i in range(self.selectedlist.count()):
                #newlist.append(unicode(self.selectedlist.item(i).text()))
            #return newlist
        #else:
            #return selectedlist

    ########################################################################
    #def slotAddClicked(self):
        #item = self.availablelist.selectedItem()
        #if item!=None:
            #self.selectedlist.insertItem(item.text())
            #self.availablelist.removeItem(self.availablelist.index(item))
            #self._selectFirstAvailable()
            #self._selectFirstSelected()
            #self.addbutton.setDisabled(self.availablelist.selectedItem()==None)
            #self.removebutton.setDisabled(self.selectedlist.selectedItem()==None)

    ########################################################################
    #def slotRemoveClicked(self):
        #item = self.selectedlist.selectedItem()
        #if item!=None:
            #self.availablelist.insertItem(item.text())
            #self.selectedlist.removeItem(self.selectedlist.index(item))
            #self._selectFirstAvailable()
            #self._selectFirstSelected()
            #self.addbutton.setDisabled(self.availablelist.selectedItem()==None)
            #self.removebutton.setDisabled(self.selectedlist.selectedItem()==None)

    ########################################################################
    #def _selectFirstAvailable(self):
        #if self.availablelist.count()!=0:
            #if self.availablelist.selectedItem()==None:
                #self.availablelist.setSelected(0,True)

    ########################################################################
    #def _selectFirstSelected(self):
        #if self.selectedlist.count()!=0:
            #if self.selectedlist.selectedItem()==None:
                #self.selectedlist.setSelected(0,True)

###########################################################################


def fix_treeview(view):
    """ Resizes all columns to contents """
    for col in range(view.model().columnCount()):
        view.resizeColumnToContents(col)


############################################################################
# Factory function for KControl
def create_userconfig(parent,name):
    return UserConfigApp(parent, name)

##########################################################################
def MakeAboutData():
    aboutdata = KAboutData("guidance", "guidance", ki18n(programname), version,
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

    KCmdLineArgs.init(sys.argv,aboutdata)

    kapp = KApplication()
    userconfigapp = UserConfigApp()
    userconfigapp.exec_()
