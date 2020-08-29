import tkinter
import numpy as np
import multiprocessing
from block import Block

def loginfo(to_display):
    text.insert(tkinter.END, to_display+'\n')

#------------------- Reads path from provided arguments and loads files --------------------------#
def initialize():

    import argparse
    parser = argparse.ArgumentParser(description='Python Synthesizer')
    parser.add_argument('--path', help='Enter path to mapping.vc', default="main_test/mapping.vc")
    args = parser.parse_args()
    
    loginfo("Creating Project at: "+ args.path)
    data = load_JSON(args.path)

    return data
#-------------------------------------------------------------------------------------------------#

#---- Loads .vc JSON object ----#
def load_JSON(file_path):

    import json
    with open(file_path) as obj:
        data = json.load(obj)
    return data
#-------------------------------#

#----- Generates Python Scripts -----#
def generate_py_script(script, script_name):

    generator = open("backend/modules/"+script_name+".py", "w")
    generator.write(script)
    generator.close()
#------------------------------------#

#----- Program exit Logic ------#
def end_progam():

    root.destroy()

    for process in processes:
        process.terminate()
        process.join()

    exit(0)
#-------------------------------#


#--------------------------- Creates Python Application from .vc File -------------------------#
def build():

    # Reading Front-End File
    data = initialize()

    # Creating dictionary of block types and their names
    # Example: (d62a6403-2db3-4832-9f4f-0f2dc8ac407d, Camera)
    info = data['dependencies']
    keys = info.keys()
    type_names = []

    for key in keys:
    
        name = info[key]['package']['name']
        type_names.append((key, name))
        loginfo("Creating Block: "+ name)
        

    # Creating dictionary of block types and their ID's
    identifiers = data['design']['graph']['blocks']

    blocks = []
    parameters_list = []
    count = 1
    for block in identifiers:

        hex_id, block_type = block['id'], block['type']

        if block_type == 'basic.code':
            
            code_name = "Code_"+str(count)
            count += 1

            script = block['data']['code']
            generate_py_script(script, code_name)

            new_block = Block(hex_id, block_type)
            new_block.name = code_name
            blocks.append(new_block)           

        elif block_type == 'basic.constant':
            parameters_list.append((hex_id, block['data']['value']))

        elif block_type == 'basic.info':
            pass

        else:
            new_block = Block(hex_id, block_type)
            new_block.set_name(type_names)
            blocks.append(new_block)


    ############# Generating Scripts for User Code & Setting Parameters #################
    for key in keys:
        
        components = info[key]['design']['graph']['blocks']
            
        for element in components:
                
            if element['type'] == 'basic.code':

                script = element['data']['code']
                scr_name = info[key]['package']['name']
                generate_py_script(script, scr_name)
            
            elif element['type'] == 'basic.constant':
                
                for block in blocks:
                    if block.id_type == key:
                        block.add_parameter(element['data']['value'])
    #####################################################################################

    # Reading Wires Mapping
    wires = data['design']['graph']['wires']


    ###################### Setting up communication between blocks ######################
    loginfo("Setting up connections...")

    wire_id = 0
    for wire in wires:

        src_block, src_port = wire['source']['block'], wire['source']['port']
        tgt_block, tgt_port = wire['target']['block'], wire['target']['port']


        # Connecting Paramters to Blocks
        if src_port == 'constant-out':

            param_value = None
            for param in parameters_list:
                if param[0] == src_block:
                    param_value = param[1]
                    break

            for block in blocks:
                if tgt_block == block.id:
                    block.add_parameter(param_value, tgt_port)
                    break

        # Connecting Wires to Blocks
        else:
            wire_name = "wire_"+str(wire_id)
            wire_id += 1

            for block in blocks:
                if tgt_block == block.id:
                    block.connect_input_wire(wire_name, tgt_port)
                    break

            for block in blocks:
                if src_block == block.id:
                    block.connect_output_wire(wire_name, src_port)
                    break
    ######################################################################################
    
    return blocks
    
#-----------------------------------------------------------------------------------------------------#
#Driver Code

if __name__ == "__main__":


    # Creating Exit Button
    root = tkinter.Tk()
    text = tkinter.Text(root)
    button = tkinter.Button(root, text = "Click here to Exit!", command = end_progam)
    text.pack()
    button.pack()

    loginfo("Building Application...")
    blocks = build()

    # Creating processes and assigning blocks. 
    loginfo("Creating Processes...")
    processes = []
    for i, element in enumerate(blocks):

        from importlib import import_module

        block_name = element.name

        if element.id_type == 'basic.code':
            method_name = 'modules.' + block_name + '.loop'
        else:
            method_name = 'modules.' + block_name + '.' + block_name

        module, function = method_name.rsplit('.',1)
        mod = import_module(module)
        method = getattr(mod, function)

        element.sort_ports()
        input_args = element.input_ports
        output_args = element.output_ports
        parameters = element.parameters

        processes.append(multiprocessing.Process(target=method,
        args=(input_args, output_args, parameters,)))

        processes[i].start()

    loginfo("Starting Application")
    root.mainloop()
