#!/usr/bin/python

import sys,os,os.path,traceback
from xml.dom.minidom import *
import copy,fnmatch
import string

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
    print message,
    for node in node_list:
        print printNode(node)+'\t\t\t',
    print(' ')

def printNode(node,print_parent=1):
    comment = ''
    if node.nodeType != Node.ELEMENT_NODE:
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



def findSameLevelChildWithId(node,ref_node):
    node_list = node.parentNode.childNodes
    for nod in node_list:
        if nod.hasAttribute('id') and (not nod.isSameNode(node)):
            ref_node = nod
            return nod
    return None


def findNextSiblingWithId(target_node):
    node = target_node
    while(node.nextSibling):
        node = node.nextSibling
        if node.nodeType == Node.ELEMENT_NODE and node.hasAttribute('id'): return node
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

def getManipulateUpgradeMetaNode(path):
    location,file_name = os.path.split(path)
    file_name,extenstion = os.path.splitext(file_name)
    upgradeMeta = Document()
    upgradeMDS = upgradeMeta.createElement('upgradeMDS')
    upgradeMeta.appendChild(upgradeMDS)
    upgradeMDS.setAttribute('enableImport','true')
    export = upgradeMeta.createElement("export")
    manipulate = upgradeMeta.createElement("manipulate")
    upgradeMDS.appendChild(export)
    upgradeMDS.appendChild(manipulate)
    manipulate.setAttribute('filename',file_name+'_*Layout*.jsff')
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

def generateAttributeScript(manipulate, operation, tagName, keyAttr, keyVal, name, value):
    last_modify = manipulate.lastChild
    if last_modify and last_modify.nodeType == Node.ELEMENT_NODE:
        flag = (keyVal == last_modify.getAttribute('keyVal')) and (tagName == last_modify.getAttribute('tagName')) and (keyAttr == last_modify.getAttribute('keyAttr'))
    doc = manipulate.ownerDocument
    if not flag:
        modify = doc.createElement('modify')
        modify.setAttribute('tagName',tagName)
        modify.setAttribute('keyAttr',keyAttr)
        modify.setAttribute('keyVal',keyVal)
        manipulate.appendChild(modify)
    else:
        modify = last_modify
    attribute = doc.createElement('attribute')
    attribute.setAttribute('operation',operation)
    attribute.setAttribute('name',name)
    if operation == 'insert':
        attribute.setAttribute('value',value)
    modify.appendChild(attribute)
    return

def generateInsertNodeScript(file_name,manipulate,reference_position,reference_tag_name,reference_key_attr,reference_key_val,
                             manipulate_component_lib,target_component_name,target_key_attr,target_key_val):
    path = file_name
    doc = manipulate.ownerDocument
    generaterRemoveNodeScript(manipulate,target_component_name,target_key_attr,target_key_val)
    insert = doc.createElement('insert')
    insert.setAttribute('position',reference_position)
    insert.setAttribute('tagName',reference_tag_name)
    insert.setAttribute('keyAttr',reference_key_attr)
    insert.setAttribute('keyVal',reference_key_val)
    manipulate.appendChild(insert)
    location,file_name = os.path.split(path)
    file_name,extenstion = os.path.splitext(file_name)
    index = string.find(file_name,'_Layout')
    file_name = file_name[:index]
    component = doc.createElement('component')
    component.setAttribute('fromPath','componentLib/')#Put in comments componentLib is hardcoded
    component.setAttribute('fileName',file_name+'.xml')
    component.setAttribute('componentName',target_component_name)
    component.setAttribute('keyAttr',target_key_attr)
    component.setAttribute('keyVal',target_key_val)
    insert.appendChild(component)

def generaterRemoveNodeScript(manipulate_node, tagName, keyAttr, keyVal):
    doc = manipulate_node.ownerDocument
    remove = doc.createElement('remove')
    remove.setAttribute('tagName',tagName)
    remove.setAttribute('keyAttr',keyAttr)
    remove.setAttribute('keyVal',keyVal)
    manipulate_node.appendChild(remove)
    return

def writeScriptsAndModifyRegistry(script_gen_path,curr_dest_file,upgrade_meta_doc,component_lib_file_doc,meta_registry_node):
    file_name = os.path.basename(curr_dest_file)
    file_name,extn = os.path.splitext(file_name)
    index = string.find(file_name,'_Layout')
    file_name = file_name[:index]
    upgrade_meta_file_name = 'UpgradeMeta_'+file_name+'.xml'
    os.chdir(script_gen_path)
    upgrade_meta_file = open(upgrade_meta_file_name,'w+')
    upgrade_meta_file.write(upgrade_meta_doc.toprettyxml(encoding='UTF-8'))
    upgrade_meta_file.close()
    os.chdir(os.path.join(script_gen_path,'componentLib'))
    component_lib_file = open(file_name+'.xml','w+')
    component_lib_file.write(component_lib_file_doc.toprettyxml(encoding='UTF-8'))
    component_lib_file.close()
    meta_node = meta_registry_node.ownerDocument.createElement('upgradeMeta')
    meta_node.setAttribute('path',upgrade_meta_file_name)
    meta_registry_node.appendChild(meta_node)


def prepareFileList(source_mds_path,dest_mds_path,relative_recur_path,source_files,dest_files,debug_flag):
    source_path = os.path.join(source_mds_path,relative_recur_path)
    dest_path = os.path.join(dest_mds_path,relative_recur_path)
    if debug_flag >= DebugFlag.FINER: print 'Looking for source files in : ',source_path,'\nLooking for Destination files in : ',dest_path
    if not (os.access(os.path.join(source_mds_path,relative_recur_path),os.R_OK) and os.access(os.path.join(dest_mds_path,relative_recur_path),os.R_OK)):
        print('Wrong path given or path not accessible.')
        exitScript(6)

    for dirpath,dirnames,filenames in os.walk(os.path.join(source_mds_path,relative_recur_path)):
        for filename in fnmatch.filter(filenames,'*.jsff'):
            source_files.append(os.path.join(dirpath,filename))
    for dirpath,dirnames,filenames in os.walk(os.path.join(dest_mds_path,relative_recur_path)):
        for filename in fnmatch.filter(filenames,'*.jsff'):
            dest_files.append(os.path.join(dirpath,filename))

    source_files.sort()
    dest_files.sort()
    source_set = set()
    dest_set = set()
    print('***********Source Files to be processed*********')
    for source_file in source_files:
        print(source_file+'\t\t'+'relative path:\t'+relativePath(source_file,source_mds_path))
        source_set.add(os.path.basename(source_file))
    print('\n**********Destination Files to be processed***********')
    for dest_file in dest_files:
        print(dest_file+'\t\t'+'relative path:\t'+relativePath(dest_file,dest_mds_path))
        dest_set.add(os.path.basename(dest_file))

    if not (source_set == dest_set):
        print("mismatch in source and destination files. Make sure both old and new mds contains same files")
        exitScript(7)
    return

def cleanUpScript():
    #This function will try to clean up un-necessary generated script eg when insert components makes the other internal change script redundant
    print("Future Clean Up Script")