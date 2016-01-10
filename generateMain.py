#!/usr/bin/python

import sys,copy,os,os.path,traceback,fnmatch
from xml.dom.minidom import *
from generateHelper import *
import var


class DebugFlag:
    LOG = 0
    FINE = 1
    FINER = 2
    FINEST = 3

WARN = '\n##### Warning: NOT GENERATING SCRIPT FOR ABOVE, NOT SUPPORTED  #####\n'

def checkForAttributeChange(manipulate_node,source_node,dest_node):
    if var.debug_flag >= DebugFlag.FINER: print'\ncheckForAttributeChange():Enter ' + printNode(source_node)
    if set(source_node.attributes.items()) == set(dest_node.attributes.items()): #Check if both nodes have same set of key-value pairs then no need to compare or generate scritps
        if var.debug_flag >= DebugFlag.FINER:
            print printNode(source_node)+' : No Attribute Changed'
            print'checkForAttributeChange():Exit '+printNode(source_node)+'\n'
        return  #This return should be out of the if condition
    if source_node.nodeName == 'jsp:root':
        if var.debug_flag >= DebugFlag.FINE:
            print '##############################################################################################################################################'
            print '############################  There are some attribute changes in jsp:root But Not Generating Script for it ##################################'
            print '##############################################################################################################################################'
        return
    if (source_node.hasAttribute('id') and source_node.getAttribute('id') in var.id_set) or (source_node.parentNode.nodeType == Node.ELEMENT_NODE and source_node.parentNode.hasAttribute('id') and source_node.parentNode.getAttribute('id') in var.id_set):
        if var.debug_flag >= DebugFlag.FINE:
            print 'Not required script for Attribute Change in '+printNode(source_node)+' this or parent node is getting inserted'
        return
    attr_set = set(list(source_node.attributes.keys()) + list(dest_node.attributes.keys()))
    if var.debug_flag >= DebugFlag.FINER : print printNode(source_node) + '  AttributeList: ',attr_set
    while(attr_set):
        attr = attr_set.pop()
        if source_node.hasAttribute(attr) and dest_node.hasAttribute(attr):
            if source_node.getAttribute(attr) == dest_node.getAttribute(attr):
                continue
            else:
                comment = 'Attribute Updated: '+attr+' '+printNode(source_node)+' modified from '+source_node.getAttribute(attr)+' to '+dest_node.getAttribute(attr)
                if var.debug_flag >= DebugFlag.FINE: print(comment)
                addCommentNode(manipulate_node,comment)
                generateAttributeScript(manipulate_node, 'insert', source_node.nodeName, 'id', source_node.getAttribute('id'),attr, dest_node.getAttribute(attr))
        elif source_node.hasAttribute(attr):
            comment = 'Attribute Removed: '+attr+' '+printNode(source_node)
            if var.debug_flag >= DebugFlag.FINE : print(comment)
            addCommentNode(manipulate_node,comment)
            generateAttributeScript(manipulate_node, 'remove', source_node.nodeName, 'id', source_node.getAttribute('id'), attr, None)
        else:
            comment =  'Attribute Added: '+attr+' '+printNode(dest_node)
            if var.debug_flag >= DebugFlag.FINE : print(comment)
            addCommentNode(manipulate_node,comment)
            generateAttributeScript(manipulate_node, 'insert', source_node.nodeName, 'id', source_node.getAttribute('id'),attr, dest_node.getAttribute(attr))
    #Future scope for development
    # What if it reports that all the Attributes of a component has been changed? Don't you think it's just id that got changed? Can you handle this?
    # why so many modify elements in scripts when all the attributes change of a single commponent could be inserted into one modify?
    if var.debug_flag >= DebugFlag.FINER: print'checkForAttributeChange():Exit ' + printNode(source_node) + '\n'
    return


def checkForChildNodeChange(manipulate_node,source_parent_node,dest_parent_node,source_child_node_list,dest_child_node_list):
    global WARN
    if var.debug_flag >= DebugFlag.FINER: print '\ncheckForChildNodeChange():Enter ' + printNode(source_parent_node)
    if not(source_child_node_list or dest_child_node_list):
        if var.debug_flag >= DebugFlag.FINER: print 'No Child Node Added or Removed'
        return
    if (source_parent_node.hasAttribute('id') and source_parent_node.getAttribute('id') in var.id_set) or (source_parent_node.parentNode.nodeType == Node.ELEMENT_NODE and source_parent_node.parentNode.hasAttribute('id') and source_parent_node.parentNode.getAttribute('id') in var.id_set):
        if var.debug_flag >= DebugFlag.FINE:
            print 'Not required script for Node Change in '+printNode(source_parent_node)+' this or parent node is getting inserted'
        return
    #Even if there is one element either inserted or deleted which doens't have ID, We will have to replace the whole parent, which means no need for further comparisons
    #need to be extra careful here as we are remove and re-inserting means always should take the dest elements
    for node in source_child_node_list + dest_child_node_list:
        if not node.hasAttribute('id'):
            comment =  '\nComponent Without ID  Added or  Removed: '+printNode(node)+'\nExperimental Feature. Trying to remove and re-insert Parent:'+printNode(node.parentNode,0)+' Not Checking Further'
            #add code to print all the removed nodes as well all the added nodes which we aren't showing.
            print comment
            if dest_parent_node.nodeType == Node.ELEMENT_NODE and dest_parent_node.hasAttribute('id'):
                insertThisNode(manipulate_node,dest_parent_node)
            elif dest_parent_node.parentNode.nodeType == Node.ELEMENT_NODE and dest_parent_node.parentNode.hasAttribute('id'):
                insertThisNode(manipulate_node,dest_parent_node.parentNode)
            else:
                print '##############################################################################################################################################'
                print '########### WARNING 3: failed to call InsertThisNode FAILED FOR : '+printNode(dest_parent_node)+'  Could not find any parent with id'
                print '##############################################################################################################################################'
            return

    for source_node in source_child_node_list:
        if source_node.hasAttribute('id'):
            #comment = 'Component removed: '+printNode(source_node)
            #if var.debug_flag >= DebugFlag.FINE: print comment
            #addCommentNode(manipulate_node,comment)
            generaterRemoveNodeScript(manipulate_node,source_node)

    for dest_node in dest_child_node_list:#IMPORTANT dest_child_node_list here is the REVERSED version of childNodes after eliminating common nodes. If we change the order the whole script will fail.
       #comment = 'Component Added : '+printNode(dest_node)
       #if var.debug_flag >= DebugFlag.FINE: print comment
       insertThisNode(manipulate_node,dest_node)
    if var.debug_flag >= DebugFlag.FINER: print 'checkForChildNodeChange():Exit ' + printNode(source_parent_node), '\n'


def insertThisNode(manipulate_node,insert_node): #insert node MUST have an ID
    #Should I need to put a check if jsp:root is the element to be inserted,if yes then return none saying root can't be replaced : Not required as insert_node must have an id mean it can't be jsp:root
    if insert_node.getAttribute('id') in var.id_set:# Do we also need to check the id of it's parent node in id set? if no correctness proof?
        print 'Node already inserted as part of another node '+printNode(insert_node)
        return
    last_child = getLastChild(insert_node.parentNode)
    ref_node_list = []
    if insert_node.isSameNode(last_child):#two cases either use position = child, which requires parent to be with id, other position = end, need atleast one sibling with id
        if insert_node.parentNode.hasAttribute('id'):
            generateInsertNodeScript(manipulate_node,'child',insert_node.parentNode,insert_node)
        elif findSameLevelChildWithId(insert_node,ref_node_list) != None:
            ref_node = ref_node_list.pop()
            generateInsertNodeScript(manipulate_node,'end',ref_node,insert_node)
        else:#this is the last node but parent doesn't have id and don't have any sibling to refer as target node eg> insertion of a compoenent in empty facet.
            if insert_node.parentNode.parentNode.nodeType == Node.ELEMENT_NODE and insert_node.parentNode.parentNode.hasAttribute('id'):
                insertThisNode(manipulate_node,insert_node.parentNode.parentNode)
            else:
                print '##############################################################################################################################################'
                print '############ WARNING 1: InsertThisNode FAILED FOR : '+printNode(insert_node) +'  ##################'
                print '##############################################################################################################################################'
    else:#find out the next sibling and use position = 'before', handle case where next sibling doesn't have id
        next_sibling = findNextSiblingWithId(insert_node)
        if next_sibling:
            generateInsertNodeScript(manipulate_node,'before',next_sibling,insert_node)
        elif insert_node.parentNode.hasAttribute('id'):#Let's try inserting the parent of current_insert node
            insertThisNode(manipulate_node,insert_node.parentNode)
        elif insert_node.parentNode.parentNode.nodeType == Node.ELEMENT_NODE and insert_node.parentNode.parentNode.hasAttribute('id'):
            insertThisNode(manipulate_node,insert_node.parentNode.parentNode)
        else:
            print '##############################################################################################################################################'
            print '############## WARNING 2: InsertThisNode FAILED FOR : '+printNode(insert_node)+'    ############'
            print '##############################################################################################################################################'
    return


def matchAndEliminateNode(to_visit,source_node_list,dest_node_list):
    temp_dest_list = []
    temp_source_list = []
    if var.debug_flag >= DebugFlag.FINER:
        print '\nmatchAndEliminate():Enter'
        print 'Before Elimination:'
        print 'Source Node List:'
        printNodeList('',source_node_list)
        print '\nDestination Node List:'
        printNodeList('',dest_node_list)
    for dest_node in dest_node_list:
        for source_node in source_node_list:
            remove_node_flag = 0
            if (dest_node.nodeName == source_node.nodeName) and ( (source_node.hasAttribute('id') and dest_node.hasAttribute('id') and source_node.getAttribute("id") == dest_node.getAttribute("id")) or set(source_node.attributes.items()) == set(dest_node.attributes.items())):
                if dest_node.hasAttribute('id') or source_node.hasChildNodes() or dest_node.hasChildNodes():
                    visit_node = (source_node,dest_node)
                    to_visit.insert(0,visit_node)
                temp_dest_list.append(dest_node)
                temp_source_list.append(source_node)
    try:
        for source_node in temp_source_list: source_node_list.remove(source_node)
        for dest_node in temp_dest_list: dest_node_list.remove(dest_node)
    except ValueError:
        print '################################################################################################'
        print '################ Error: Two Child with same set of attributes or With same ID ##################'
        print traceback.print_exc()
        print '################################################################################################'

    if source_node_list:
        printNodeList('Component Removed:',source_node_list)
    if dest_node_list:
        printNodeList('Component Added: ',dest_node_list)
    if var.debug_flag >= DebugFlag.FINER:
        print '\nmatchAndEliminate():Exit'
    return


def modifiedDFS(to_visit,manipulate_node,meta_registry_node):
    file_name = os.path.basename(var.curr_dest_file)
    index = string.find(file_name,'_Layout')
    file_name = file_name[:index]+'.jsff'
    print '\n\n\n************ Modifying : '+file_name+' ********************'
    while(to_visit):
        if var.debug_flag >= DebugFlag.FINER: print '\nto_visit[]: ',to_visit
        source_parent_node,dest_parent_node = to_visit.pop(0)
        if var.debug_flag >= DebugFlag.FINER: print 'Now Visiting: ' + printNode(dest_parent_node)
        source_child_node_list = copy.copy(source_parent_node.childNodes)
        dest_child_node_list = copy.copy(dest_parent_node.childNodes)
        source_child_node_list.reverse()
        dest_child_node_list.reverse()
        checkForAttributeChange(manipulate_node,source_parent_node,dest_parent_node)
        matchAndEliminateNode(to_visit,source_child_node_list,dest_child_node_list)
        checkForChildNodeChange(manipulate_node,source_parent_node,dest_parent_node,source_child_node_list,dest_child_node_list)
#    doc = manipulate_node.ownerDocument
#    component_doc = component_lib_file_root.ownerDocument
#    file_name = os.path.basename(curr_dest_file)
#    index = string.find(file_name,'_Layout')
#    file_name = file_name[:index]
#    print ('\n++++++++++++++++++++  WARNINGS : '+file_name+' +++++++++++++++++++++++')
#    for warn in warnings:
#        print warn
#    print("\n\n+++++++++++++++++Upgrade Script++++++++++++++++++++")
#    print(doc.toprettyxml())
#    print("\n+++++++++++++++++ComponentLib File++++++++++++++++++++")
#    print(component_doc.toprettyxml())

    writeScriptsAndModifyRegistry(manipulate_node,meta_registry_node)
    var.id_set.clear()
    return



def processAndValidateScriptParameters():
    Syntax = 'generateMain.py  old_mds_path  new_mds_path  dir_path_relative_to_mds  script_gen_path  debug_flag(optional)'
    if not (len(sys.argv) ==5 or len(sys.argv) == 6):
        print("Wrong arguement passed\n"+Syntax)
        exitScript(1)
    var.source_mds_path = sys.argv[1]
    if not os.path.exists(var.source_mds_path):
        print 'Source MDS Path Does not Exist: '+ var.source_mds_path
        exitScript(1)
    var.dest_mds_path = sys.argv[2]
    if not os.path.exists(var.dest_mds_path):
        print 'Destination MDS Path Does Not Exist : '+var.dest_mds_path
        exitScript(1)
    var.relative_recur_path = sys.argv[3]
    var.script_gen_path = sys.argv[4]
    if not os.access(var.dest_mds_path,os.W_OK):
        print 'Script Gen Path : No Write Access or Path does not exist : '+var.script_gen_path
        exitScript(1)
    try:
        if(len(sys.argv) == 6):
            var.debug_flag = int(sys.argv[5])
    except Exception:
        print("Provide integer value for debug flag")
        exitScript(1)

def initProcess():
    to_visit = []
    processAndValidateScriptParameters()
    meta_registry_node = getUpgradeMetaRegistryNode()
    prepareFileList()
    for var.curr_source_file, var.curr_dest_file in zip(var.source_files, var.dest_files):
        if not os.path.basename(var.curr_source_file) == os.path.basename(var.curr_dest_file):
            print("mismatch in source and destination files. Make sure both old and new mds contains same files")
            exitScript(4)
        else:
            source_dom = parse(var.curr_source_file)
            dest_dom = parse(var.curr_dest_file)
            source_root = source_dom.documentElement
            dest_root = dest_dom.documentElement
            visit_node = (source_root,dest_root)
            to_visit.append(visit_node)
            cleanDOM(source_root)
            cleanDOM(dest_root)
            manipulate_node = getManipulateUpgradeMetaNode(relativePath(var.curr_dest_file, var.dest_mds_path))
            var.component_lib_file_root = getComponentLibFileRoot(dest_dom)
            modifiedDFS(to_visit,manipulate_node,meta_registry_node)
    os.chdir(var.script_gen_path)
    upgrade_meta_registry_file = open('upgradeMetaRegistry.xml','w+')
    upgrade_meta_registry_file.write(meta_registry_node.ownerDocument.toprettyxml(encoding='UTF-8'))
    upgrade_meta_registry_file.close()
    return

initProcess()

'''to do
If Experimental Feature working fine then need to optimize checkChildNodeChange() Function as there is lot of redundancy
2. push all the warnings into a single file along with those components
3. unnecessary componentLib generation.

debug level
support for only id change
check for possible duplicate id after insert
try to validate xml

at the moment c:set and jsp:root are the only contnious non-id elements in tree.

Add below function for easy comparison of before and after upgrade script run
 def writeXml(path):
	dom = parse(path)
	fl = open('test.jsff','w+')
	fl.write(dom.toxml(encoding='UTF-8'))
	f1.close()
Done:---
4. creating upgradeMetaRegistry
3. writing the generated scripts in newly created updatemeta and componentLib files
In matchAndEliminateNode() Add support to check if a node without id has similar attributes using sets and subsets, even if I attribute defers we need to generate script for removing and re-inserting parent node
clubbing the all attribute changes in one modify tag
don't just insert, remove and re-insert


'''