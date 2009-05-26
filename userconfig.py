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

        if standalone:
            QWidget.__init__(self)
            if os.path.exists('ui/maindialog.ui'): 
                self.md = uic.loadUi('ui/maindialog.ui', self)
        #FIXME: SRSLY! Need to know where the ui crap'll be installed and check for it there too.
        else:
            KCModule.__init__(self,parent,name)
            self.setButtons(0)
            self.aboutdata = MakeAboutData()

            toplayout = KVBoxLayout( self, 0, KDialog.spacingHint() )
            tabcontrol = QTabWidget(self)
            toplayout.addWidget(tabcontrol)
            toplayout.setStretchFactor(tabcontrol,1)

        # Create a configuration object.
        self.config = KConfig("userconfigrc")

        KIconLoader.global_().addAppDir("guidance")

        self.usersToListItems = None
        self.selecteduserid = None
        self.selectedgroupid = None
        self.showsystemaccounts = False
        self.showsystemgroups = False

        self.updatingGUI = True



        #self.aboutus = KAboutApplicationDialog(self) #TODO

        #self.md.accountLabel.setPixmap(KIcon('user-identity')) #TODO

        self.connect(self.md.userlist, SIGNAL("currentItemChanged ( QTreeWidgetItem *, QTreeWidgetItem *)"), self.slotListClicked)
        if isroot:
            self.connect(self.md.userlist, SIGNAL("doubleClicked(QListViewItem *)"), self.slotModifyClicked)
        self.connect(self.md.userlist, SIGNAL("contextMenu(KListView*,QListViewItem*,const QPoint&)"), self.slotUserContext)

        self.connect(self.md.showspecialcheckbox,SIGNAL("toggled(bool)"), self.slotShowSystemToggled)

        self.connect(self.md.modifybutton,SIGNAL("clicked()"),self.slotModifyClicked)

        self.connect(self.md.newbutton,SIGNAL("clicked()"),self.slotNewClicked)

        self.connect(self.md.deletebutton,SIGNAL("clicked()"),self.slotDeleteClicked)

        userdetails_groupbox = self.md.userdetails_groupbox

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


        #FIXME: Need to find Oxygen group icon
        #self.groupLabel.setPixmap(KIcon('user-identity')) #Also need to do this right, lolz

        
        self.grouplist = self.md.grouplist
        self.connect(self.grouplist, SIGNAL("currentItemChanged( QTreeWidgetItem *, QTreeWidgetItem *)"), self.slotGroupListClicked)

        if isroot:
            self.connect(self.grouplist, SIGNAL("doubleClicked(QListViewItem *)"), self.slotModifyGroupClicked)
        self.connect(self.grouplist, SIGNAL("contextMenu(KListView*,QListViewItem*,const QPoint&)"), 
                self.slotGroupContext)

        self.connect(self.md.showspecialgroupscheckbox,SIGNAL("toggled(bool)"), self.slotShowSystemGroupsToggled)

        self.connect(self.md.modifygroupbutton,SIGNAL("clicked()"),self.slotModifyGroupClicked)

        self.connect(self.md.newgroupbutton,SIGNAL("clicked()"),self.slotNewGroupClicked)

        self.connect(self.md.deletegroupbutton,SIGNAL("clicked()"),self.slotDeleteGroupClicked)

        if not isroot:
            disablebuttons = (  self.md.modifybutton, self.md.modifygroupbutton, self.md.deletebutton, self.md.deletegroupbutton,
                                self.md.newbutton, self.md.newgroupbutton)
            for widget in disablebuttons:
                widget.setDisabled(True)

        #FIXME Need to handle non-standalone when it can be non-standalone
        #if not standalone:
            #tabcontrol.addTab(groupsvbox,i18n("Groups"))

        self.admincontext = unixauthdb.getContext(isroot)

        self.updatingGUI = True

        self.md.showspecialcheckbox.setChecked(self.showsystemaccounts)
        self.md.showspecialgroupscheckbox.setChecked(self.showsystemgroups)

        self.__updateUserList()
        self.__updateGroupList()
        self.updatingGUI = False

        self.usereditdialog = UserEditDialog(None,self.admincontext)
        self.userdeletedialog = UserDeleteDialog(None,self.admincontext)
        self.groupeditdialog = GroupEditDialog(None,self.admincontext)

    #######################################################################
    def exec_(self):
        global programbase
        self.__loadOptions()
        self.updatingGUI = True
        self.__updateUserList()
        self.__updateGroupList()
        self.updatingGUI = False
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
        size_hint.setHeight(size_hint.height()-200) 
        return size_hint

    #######################################################################
    def slotCloseButton(self):
        self.close()

    #######################################################################
    def slotListClicked(self,item, previousitem):
        if self.updatingGUI==False:
            for userid in self.useridsToListItems:
                if self.useridsToListItems[userid]==item:
                    self.updatingGUI = True
                    self.__selectUser(userid)
                    self.updatingGUI = False
                    return

    #######################################################################
    def slotShowSystemToggled(self,on):
        self.showsystemaccounts = on
        if self.updatingGUI==False:
            self.updatingGUI = True
            self.__updateUserList()
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
        if newuid!=None:
            self.updatingGUI = True
            self.__updateUserList()
            self.__selectUser(newuid)
            self.__updateGroupList()
            self.updatingGUI = False

    #######################################################################
    def slotDeleteClicked(self):
        if self.userdeletedialog.deleteUser(self.selecteduserid):
            self.updatingGUI = True
            self.selecteduserid = None
            self.__updateUserList()
            self.__updateGroupList()
            self.updatingGUI = False

    #######################################################################
    def slotGroupListClicked(self,item):
        if self.updatingGUI==False:
            for groupid in self.groupidsToListItems:
                if groupid and self.groupidsToListItems[groupid]==item:
                    self.updatingGUI = True
                    self.__selectGroup(groupid)
                    self.updatingGUI = False
                    return

    #######################################################################
    def slotShowSystemGroupsToggled(self,on):
        self.showsystemgroups = on
        if self.updatingGUI==False:
            self.updatingGUI = True
            self.__updateGroupList()
            self.updatingGUI = False

    #######################################################################
    def slotModifyGroupClicked(self):
        if self.selectedgroupid!=None:
            if self.groupeditdialog.showEditGroup(self.selectedgroupid):
                self.__selectGroup(self.selectedgroupid)
                self.updatingGUI = True
                self.__updateUser(self.selecteduserid)
                self.__selectUser(self.selecteduserid)
                self.updatingGUI = False

    #######################################################################
    def slotNewGroupClicked(self):
        newgroupid = self.groupeditdialog.showNewGroup()
        if newgroupid!=None:
            self.updatingGUI = True
            self.__updateGroupList()
            self.__updateGroupList()
            self.__selectGroup(newgroupid)
            self.__updateUser(self.selecteduserid)
            self.__selectUser(self.selecteduserid)
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
                self.__updateGroupList()
                self.__updateUser(self.selecteduserid)
                self.__selectUser(self.selecteduserid)
                self.updatingGUI = False

    #######################################################################
    def __updateUserList(self):
        self.md.userlist.clear()
        self.useridsToListItems = {}
        firstselecteduserid = None

        users = self.admincontext.getUsers()

        for userobj in users:
            uid = userobj.getUID()
            if self.showsystemaccounts or not userobj.isSystemUser():
                itemstrings = QStringList()
                itemstrings.append(userobj.getUsername())
                itemstrings.append(userobj.getRealName())
                itemstrings.append(unicode(uid))
                lvi = QTreeWidgetItem(self.md.userlist,itemstrings)
                if userobj.isLocked():
                    # TODO
                    pass
                    #lvi.setPixmap(0,UserIcon("hi16-encrypted"))
                self.useridsToListItems[uid] = lvi
                if self.selecteduserid==uid:
                    firstselecteduserid = uid
                elif firstselecteduserid==None:
                    firstselecteduserid = uid
        self.selecteduserid = firstselecteduserid
        self.__selectUser(self.selecteduserid)
        #self.userlist.ensureItemVisible(self.userlist.currentItem())

    #######################################################################
    def __updateUser(self,userid):
        lvi = self.useridsToListItems[userid]
        userobj = self.admincontext.lookupUID(userid)
        lvi.setText(0,userobj.getUsername())
        lvi.setText(1,userobj.getRealName())
        lvi.setText(2,unicode(userobj.getUID()))
        if userobj.isLocked():
            pass
            #lvi.setPixmap(0,UserIcon("hi16-encrypted")) # TODO
        else:
            pass
            #lvi.setPixmap(0,QPixmap())  # TODO

    #######################################################################
    def __selectUser(self,userid):
        print 'Setting user ID to', userid
        self.selecteduserid = userid
        # Only go on if there are actual users.
        if len(self.useridsToListItems)>0:
            lvi = self.useridsToListItems[userid]
            #self.userlist.setSelected(lvi,True)
            self.md.userlist.setCurrentItem(lvi)

            userobj = self.admincontext.lookupUID(userid)

            username = userobj.getUsername()
            self.md.loginnamelabel.setText(username)
            self.md.realnamelabel.setText(userobj.getRealName())
            self.md.uidlabel.setText(unicode(userid))
            if userobj.isLocked():
                self.md.statuslabel.setText(i18n("Disabled"))
            else:
                self.md.statuslabel.setText(i18n("Enabled"))

            # Primary Group
            primarygroupobj = userobj.getPrimaryGroup()
            primarygroupname = primarygroupobj.getGroupname()
            self.md.primarygrouplabel.setText(primarygroupname)

            # Secondary Groups
            secondarygroups = [g.getGroupname() for g in userobj.getGroups() if g is not userobj.getPrimaryGroup()]
            self.md.secondarygrouplabel.setText(unicode(i18n(", ")).join(secondarygroups))

            if isroot:
                self.md.deletebutton.setDisabled(userobj.getUID()==0)

    #######################################################################
    def __updateGroupList(self):
        self.grouplist.clear()
        self.groupidsToListItems = {}
        firstselectedgroupid = None

        groups = self.admincontext.getGroups()
        for groupobj in groups:
            gid = groupobj.getGID()
            if self.showsystemgroups or not groupobj.isSystemGroup():
                itemstrings = QStringList()
                itemstrings.append(groupobj.getGroupname())
                itemstrings.append(unicode(gid))
                lvi = QTreeWidgetItem(self.grouplist,itemstrings)
                self.groupidsToListItems[gid] = lvi
                if self.selectedgroupid==gid:
                    firstselectedgroupid = gid
                elif firstselectedgroupid==None:
                    firstselectedgroupid = gid
        self.selectedgroupid = firstselectedgroupid
        self.__selectGroup(self.selectedgroupid)
        #self.grouplist.ensureItemVisible(self.grouplist.currentItem())

    #######################################################################
    def __selectGroup(self,groupid):
        print 'Setting group ID to', groupid
        if groupid:
            self.selectedgroupid = groupid
            lvi = self.groupidsToListItems[groupid]
            #self.grouplist.setSelected(lvi,True)
            self.grouplist.setCurrentItem(lvi)

            groupobj = self.admincontext.lookupGID(groupid)
            members = groupobj.getUsers()
            self.md.groupmemberlist.clear()
            for userobj in members:
                if userobj!=None:
                    itemstrings = QStringList()
                    itemstrings.append(userobj.getUsername())
                    itemstrings.append(userobj.getRealName())
                    itemstrings.append(unicode(userobj.getUID()))
                    lvi = QTreeWidgetItem(self.md.groupmemberlist,itemstrings)
            if isroot:
                self.md.deletegroupbutton.setDisabled(groupobj.getGID()==0)

    #######################################################################
    def __loadOptions(self):
        #self.config.setGroup("General")
        
        size = self.config.group("General").readEntry("Geometry")
        #if size.isEmpty()==False:
            #self.resize(size)  # TODO
        #self.config.setGroup("Options")
        self.showsystemaccounts = self.config.group("Options").readEntry("ShowSystemAccounts")
        if self.showsystemaccounts == '':
            self.showsystemaccounts == 0
        else:
            self.showsystemaccounts = int(self.showsystemaccounts)
        self.md.showspecialcheckbox.setChecked(bool(self.showsystemaccounts))
        self.showsystemgroups = self.config.group("Options").readEntry("ShowSystemGroups")
        if self.showsystemgroups == '':
            self.showsystemgroups == 0
        else:
            self.showsystemgroups = int(self.showsystemgroups)
        self.md.showspecialgroupscheckbox.setChecked(bool(self.showsystemgroups))

    #######################################################################
    def __saveOptions(self):
        global isroot
        if isroot:
            return
        #self.config.setGroup("General")
        #self.config.group("General").writeEntry("Geometry", self.size())   # TODO
        #self.config.setGroup("Options")
        self.config.group("Options").writeEntry("ShowSystemAccounts",str(int(self.showsystemaccounts)))
        self.config.group("Options").writeEntry("ShowSystemGroups",str(int(self.showsystemgroups)))
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




############################################################################
# Factory function for KControl
def create_userconfig(parent,name):
    return UserConfigApp(parent, name)

##########################################################################
def MakeAboutData():
    aboutdata = KAboutData("guidance", "guidance", ki18n(programname), version,
        ki18n("User and Group Configuration Tool"),
        KAboutData.License_GPL, ki18n("Copyright (C) 2003-2007 Simon Edwards"))
    aboutdata.addAuthor(ki18n("Simon Edwards"), ki18n("Developer"), "simon@simonzone.com", "http://www.simonzone.com/software/")
    aboutdata.addAuthor(ki18n("Sebastian Kügler"), ki18n("Developer"), "sebas@kde.org", "http://vizZzion.org")
    aboutdata.addAuthor(ki18n("Yuriy Kozlov"), ki18n("Developer"), "yuriy-kozlov@kubuntu.org", "http://www.yktech.us")
    return aboutdata

if standalone:
    aboutdata = MakeAboutData()

    KCmdLineArgs.init(sys.argv,aboutdata)

    kapp = KApplication()
    userconfigapp = UserConfigApp()
    userconfigapp.exec_()
