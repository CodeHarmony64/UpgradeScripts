source_mds_path = ''                        #script parameter to store path of the old/source mds
dest_mds_path = ''                          #script parameter to store path of the new/destination mds
relative_recur_path = ''                    #script parameter to store path of the directory which needs to be search recursively to look for respective source and destinaiton files relative to mds location
script_gen_path = ''                        #script parameter to store path where the new scripts will be generated
debug_flag = 0                              #script parameter to store debug flag can be 0 for Logs, 1 for Fine, 2 for finer, 3 for finest


source_files = []                           #Global variable to store the list of all the source files that needs to be checked along absolute path
dest_files = []                             #Global variable to store the list of all the destination files that needs to be compared along with absolute path


#Below mentioned global variables Require reset after each modifiedDFS iteration
curr_source_file = ''                       #Global variable : Holds the source file currently being processed.
curr_dest_file = ''                         #Global variable : Holds the destination file currenlty being processed.
warnings = []                               #Global List : Holds all the warnings for files currently being processed
id_set = set()                              #Global Set : Holds all the component and their children's ids which are already been inserted
manipulate_node = None                      #Global Node : Holds the reference to the maniuplate node of current UpgradeMeta, all the generated script nodes are appended to it
component_lib_file_root = None              #Global variable to hold the refrence to root node of component Lib. All upgradeMeta nodes will be appended to this