#!/usr/bin/python

import sys,os,os.path,traceback
from xml.dom.minidom import *
import copy,fnmatch
import string,var

class DebugFlag:
    FINE = 1
    FINER = 2
    FINEST = 3

def exitScript(n):
    print("exiting")
    sys.exit(n)

def relativePath(path,relativ_to): #try catch block can be added to handle to see this doesn't return malformed path
    return path.replace(relativ_to,'',1)

def appendList(st,lst):#Adds all the items of the list to an existing set
    for itm in lst:
        st.add(itm)
    return

def printNodeList(message,node_list):# prints message + all the nodes in nodeList
    for node in node_list:
        print '\t\t'+message + printNode(node)

def printNode(node,print_parent=1):
    comment = ''
    if not node:
        return 'None'
    elif node.nodeType != Node.ELEMENT_NODE:
        comment = 'Node :Text Node'
    elif node.hasAttribute('id'):
        comment = node.nodeName+' id:'+node.getAttribute('id')
    elif node.nodeName == 'f:facet':
        comment = node.nodeName+' name:'+node.getAttribute('name')
    elif node.nodeName == 'c:set':
        comment = node.nodeName+' var:'+node.getAttribute('var')+' value:'+node.getAttribute('value')
    elif node.nodeName == 'af:setActionListener':
        comment = node.nodeName+' from:'+node.getAttribute('from')+' to:'+node.getAttribute('to')
    else:
        comment = node.nodeName

    if(print_parent and node.parentNode.nodeType == Node.ELEMENT_NODE):
        comment = comment+' Parent: '+printNode(node.parentNode,0)

    return comment

def findSameLevelChildWithId(node,ref_node_list):
    node_list = node.parentNode.childNodes
    for nod in node_list:
        if nod.hasAttribute('id') and (not nod.isSameNode(node)):
            ref_node_list.append(nod)
            return nod
    return None


def findNextSiblingWithId(target_node):#it should ignore the NON Element Node but very first Element node should be returned having id shouldn't matter or we can return none in case next sibling is non id
    node = target_node
    while(node.nextSibling):
        node = node.nextSibling
        if node.nodeType == Node.ELEMENT_NODE:
            if node.hasAttribute('id'):
                return node
            return None
    return None

def getLastChild(node): #Return the last element child of any node
    last_child = node.lastChild
    while last_child.previousSibling:
        if last_child.nodeType == Node.ELEMENT_NODE:
            return last_child
        last_child = last_child.previousSibling
    return None

def cleanDOM(root):
    if root:
        nodeList = root.childNodes
        temp_list = copy.copy(nodeList)
        for node in temp_list:
            if node.nodeType  == Node.TEXT_NODE or node.nodeType == Node.COMMENT_NODE or node.nodeType == Node.CDATA_SECTION_NODE:
                nodeList.remove(node)
        for node in nodeList:
            cleanDOM(node)
    return

def addCommentNode(root,data):
    doc = root.ownerDocument
    #root.appendChild(doc.createComment(data))

def addNodeIdsToSet(node):
    if not node or node.nodeType != Node.ELEMENT_NODE:
        return
    if node.hasAttribute('id'):
        var.id_set.add(node.getAttribute('id'))
    for nod in node.childNodes:
        addNodeIdsToSet(nod)

def getManipulateUpgradeMetaNode(path):
    location,file_name = os.path.split(path)
    location = os.path.join(location,'')
    index = string.find(file_name,'_Layout')
    file_name = file_name[:index]
    upgradeMeta = Document()
    upgradeMDS = upgradeMeta.createElement('upgradeMDS')
    upgradeMeta.appendChild(upgradeMDS)
    upgradeMDS.setAttribute('enableImport','true')
    export = upgradeMeta.createElement("export")
    manipulate = upgradeMeta.createElement("manipulate")
    upgradeMDS.appendChild(export)
    upgradeMDS.appendChild(manipulate)
    manipulate.setAttribute('fileName',file_name+'_*Layout*.jsff')
    manipulate.setAttribute('type','update')
    manipulate.setAttribute('location',location)
    export.setAttribute('doc',os.path.join(location,'*'))
    return manipulate


def getComponentLibFileRoot(dest_dom):
    component_lib_file = Document()
    root = dest_dom.documentElement
    compoent_lib_file_root = component_lib_file.createElement(root.tagName)
    attributes = root.attributes.items()
    for attribute in attributes:
        compoent_lib_file_root.setAttribute(attribute[0],attribute[1])
    component_lib_file.appendChild(compoent_lib_file_root)
    return compoent_lib_file_root

def getUpgradeMetaRegistryNode(description = "ActivityManagementAutomated"):
    upg_meta_registry = Document()
    upgrade_meta_list = upg_meta_registry.createElement('upgradeMetaList')
    upgrade_meta_list.setAttribute('coreScriptVersion',"1.0")
    upgrade_meta_list.setAttribute('description',description)
    upg_meta_registry.appendChild(upgrade_meta_list)
    return upgrade_meta_list

def generateAttributeScript(operation,name,node):
    last_modify = var.manipulate_node.lastChild
    flag = 0
    doc = var.manipulate_node.ownerDocument
    if last_modify and last_modify.nodeType == Node.ELEMENT_NODE:
        flag = node.nodeName == last_modify.getAttribute('tagName') and node.hasAttribute('id') and node.getAttribute('id') == last_modify.getAttribute('keyVal')
    if node.nodeName == 'jsp:root':
        modify = doc.createElement('modify')
        modify.setAttribute('tagName',node.nodeName)
        modify.setAttribute('keyAttr','version')
        modify.setAttribute('keyVal',node.getAttribute('version'))
        var.manipulate_node.appendChild(modify)
    elif not flag:
        modify = doc.createElement('modify')
        modify.setAttribute('tagName',node.nodeName)
        modify.setAttribute('keyAttr','id')
        modify.setAttribute('keyVal',node.getAttribute('id'))
        var.manipulate_node.appendChild(modify)
    else:
        modify = last_modify
    attribute = doc.createElement('attribute')
    attribute.setAttribute('operation',operation)
    attribute.setAttribute('name',name)
    if operation == 'insert':
        attribute.setAttribute('value',node.getAttribute(name))
    modify.appendChild(attribute)
    return

def generateInsertNodeScript(reference_position,ref_node,target_node):
    path = var.curr_dest_file
    doc = var.manipulate_node.ownerDocument
    generaterRemoveNodeScript(target_node)
    insert = doc.createElement('insert')
    insert.setAttribute('position',reference_position)
    insert.setAttribute('tagName',ref_node.nodeName)
    insert.setAttribute('keyAttr','id')
    insert.setAttribute('keyVal',ref_node.getAttribute('id'))
    var.manipulate_node.appendChild(insert)
    location,file_name = os.path.split(path)
    file_name,extenstion = os.path.splitext(file_name)
    index = string.find(file_name,'_Layout')
    file_name = file_name[:index]
    component = doc.createElement('component')
    component.setAttribute('fromPath',os.path.join('componentLib',''))#Put in comments componentLib is hardcoded
    component.setAttribute('fileName',file_name+'.xml')
    component.setAttribute('componentName',target_node.nodeName)
    component.setAttribute('keyAttr','id')
    component.setAttribute('keyVal',target_node.getAttribute('id'))
    insert.appendChild(component)
    addNodeIdsToSet(target_node)
    var.component_lib_file_root.appendChild(copy.deepcopy(target_node))


def generaterRemoveNodeScript(remove_node):
    doc = var.manipulate_node.ownerDocument
    remove = doc.createElement('remove')
    remove.setAttribute('tagName', remove_node.nodeName)
    remove.setAttribute('keyAttr','id')
    remove.setAttribute('keyVal', remove_node.getAttribute('id'))
    var.manipulate_node.appendChild(remove)
    return

def writeScriptsAndModifyRegistry(meta_registry_node):
    if var.manipulate_node.hasChildNodes():
        cleanUpgradeMeta()
        upgrade_meta_doc = var.manipulate_node.ownerDocument
        file_name = os.path.basename(var.curr_dest_file)
        file_name,extn = os.path.splitext(file_name)
        index = string.find(file_name,'_Layout')
        file_name = file_name[:index]
        upgrade_meta_file_name = 'UpgradeMeta_'+file_name+'.xml'
        os.chdir(var.script_gen_path)
        upgrade_meta_file = open(upgrade_meta_file_name,'w+')
        upgrade_meta_file.write(upgrade_meta_doc.toprettyxml(encoding='UTF-8'))
        upgrade_meta_file.close()
        if var.component_lib_file_root.hasChildNodes():
            component_lib_file_doc = var.component_lib_file_root.ownerDocument
            os.chdir(os.path.join(var.script_gen_path, 'componentLib'))
            component_lib_file = open(file_name+'.xml','w+')
            component_lib_file.write(component_lib_file_doc.toprettyxml(encoding='UTF-8'))
            component_lib_file.close()
        meta_node = meta_registry_node.ownerDocument.createElement('upgradeMeta')
        meta_node.setAttribute('path',upgrade_meta_file_name)
        meta_registry_node.appendChild(meta_node)


def prepareFileList():
    source_path = os.path.join(var.source_mds_path, var.relative_recur_path)
    dest_path = os.path.join(var.dest_mds_path, var.relative_recur_path)
    if var.debug_flag >= DebugFlag.FINER: print 'Looking for source files in : ',source_path, '\nLooking for Destination files in : ',dest_path
    if not (os.access(os.path.join(var.source_mds_path, var.relative_recur_path), os.R_OK) and os.access(os.path.join(var.dest_mds_path, var.relative_recur_path), os.R_OK)):
        print('Wrong path given or path not accessible.')
        exitScript(6)

    for dirpath,dirnames,filenames in os.walk(os.path.join(var.source_mds_path, var.relative_recur_path)):
        for filename in fnmatch.filter(filenames,'*.jsff'):
            var.source_files.append(os.path.join(dirpath, filename))
    for dirpath,dirnames,filenames in os.walk(os.path.join(var.dest_mds_path, var.relative_recur_path)):
        for filename in fnmatch.filter(filenames,'*.jsff'):
            var.dest_files.append(os.path.join(dirpath, filename))

    var.source_files.sort()
    var.dest_files.sort()
    source_set = set()
    dest_set = set()
    print('***********Source Files to be processed*********')
    for source_file in var.source_files:
        print(source_file +'\t\t' +'relative path:\t' + relativePath(source_file, var.source_mds_path))
        source_set.add(os.path.basename(source_file))
    print('\n**********Destination Files to be processed***********')
    for dest_file in var.dest_files:
        print(dest_file +'\t\t' +'relative path:\t' + relativePath(dest_file, var.dest_mds_path))
        dest_set.add(os.path.basename(dest_file))

    if not (source_set == dest_set):
        print("mismatch in source and destination files. Make sure both old and new mds contains same files")
        exitScript(7)
    return

def cleanUpScript():
    #This function will try to clean up un-necessary generated script eg when insert components makes the other internal change script redundant
    print("Future Clean Up Script")

def findFirstNonRemoveManipulateChild():
    for node in var.manipulate_node.childNodes:
        if node.nodeName != 'remove':
            return node
    return None

def cleanUpgradeMeta():
    before_node = findFirstNonRemoveManipulateChild()
    if not before_node:
        return
    remove_node_list = []
    for node in var.manipulate_node.childNodes:
        if node.nodeName == 'remove':
            remove_node_list.append(node)
    for node in remove_node_list:
        var.manipulate_node.insertBefore(node,before_node)
    return






