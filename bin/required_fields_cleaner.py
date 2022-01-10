import collections
import yaml
import sys
import glob
import os
import re
import json

#find datamodel=SOMETHING, allowing for whitespace on either side of =
DATAMODEL_PATTERN = r"datamodel\s*=?\s*\S*"

QUOTATIONS_PATTERN = r'''(["'])(?:(?=(\\?))\2.)*?\1'''
KEY_VALUE_PATTERN = r"[a-zA-Z0-9_]*\.[a-zA-Z0-9_]*"

def dictPrint(d):
    import pprint
    printer = pprint.PrettyPrinter(indent=3)
    printer.pprint(d)


def parse_datamodel(datamodel_name, object)->dict:
    submodules = {}
    if "objects" in object:
        raise(Exception(("nested objects!")))

    #print(object.keys())
    
    #print(object['calculations'])
    #input("W")
    allFields = []
    if 'fields' in object:
        allFields += object['fields']

    if 'calculations' in object:
        for calc_dict in object['calculations']:
            if 'outputFields' in calc_dict:
                allFields += calc_dict['outputFields']
        
    
    for field in allFields:
        
        fieldName = field['fieldName']
        if fieldName in submodules:
            raise(Exception(f"Duplicate Field {field} in {datamodel_name}"))
        
        submodel_fieldname = f"{object['objectName']}.{fieldName}"
        model_submodel_fieldname =  f"{datamodel_name}.{submodel_fieldname}"
        submodules[fieldName] = {"field_name": fieldName, "submodel.fieldname": submodel_fieldname, "datamodel.submodel.field_name": model_submodel_fieldname}
        

    return submodules

def load_datamodels_from_directory(datamodels_directory:str)->dict:
    all_models = {}
    datamodel_filenames = glob.glob(os.path.join(datamodels_directory,"*.json"))    
    for datamodel_filename in datamodel_filenames:
        #Load the YAML File
        with open(datamodel_filename, "r") as model_stream:
            json_datamodel = json.load(model_stream)

        model_name = json_datamodel['modelName']
        model_fields = {}

        #Load all the submodels from the YAML file
        for submodel in json_datamodel['objects']:
            model_fields[submodel['objectName']] = parse_datamodel(model_name, submodel)
        
        print("All datamodels parsed")
        all_models[model_name] = model_fields
    
    '''
    dups = [{"field_name": element, "number_of_occurences":count} for element, count in collections.Counter(all_fields).items() if count > 1]
    if len(dups) != 0:
        print("There were duplicate field names in the data models. They are listed below")
        for dup in dups:
            print(f"{dup['field_name']}: {dup['number_of_occurences']} occurences")
        raise Exception("Duplicate fields detected")
    '''
    '''
    counts= {}
    for field in all_fields:
        c = field.count(".")
        if c in counts:
            counts[c] += 1
        else:
            counts[c] = 1
    print(counts)

    print("\n".join(all_fields))
    '''

    return all_models


def get_datamodels(search:str)->set[str]:
    #print(search)
    matches = re.findall(DATAMODEL_PATTERN, search)

    #get the models and strip out the whitespace
    
    #If we want different dot-separated versions
    
    models_and_submodels = [model.replace(" ","=").split("=")[1].strip() for model in matches]

    #If we only care about the top level
    models_only = [model.split(".")[0].strip() for model in models_and_submodels]

    
    return set(models_only)

def get_tokens(search:str):
    quoted_text_removed = re.sub(QUOTATIONS_PATTERN, "", search)
    return set(re.findall(KEY_VALUE_PATTERN, quoted_text_removed))


def update_required_fields_for_yaml(filename:str, search:str, required_fields:set, datamodels_from_datamodel_field:set, defined_datamodels:dict)->dict:
    datamodels_from_search = get_datamodels(search)
    #print(f"Datamodels found in {filename}: {datamodels}")
    yaml_fields_to_update = {}
    yaml_update_required = False
    if len(datamodels_from_search) > 0:
        for model in datamodels_from_search:
            if model.count(".") > 1:
                print(f"{filename} contains Datamodel '{model}'.\nDatamodel MUST be in format Model or Model.Submodel", file=sys.stderr)
                sys.exit(1)
    

        
    
   



    disjoint_members = datamodels_from_datamodel_field.symmetric_difference(datamodels_from_search)
    if len(disjoint_members) != 0:
        yaml_update_required = True
    '''
    for model in datamodels_from_datamodel_field:
        if model not in datamodels_from_search:
            #print(f"file {filename} yml contains datamodels:{datamodels} but {model} was not found in search: {search}")
            #print("ERROR")
            yaml_update_required = True
            #input("waiting...\n")
    
    for model in datamodels_from_search:
        if model not in datamodels_from_datamodel_field:
            #print(f"file {filename} yml contains search: {search} but {model} was not found in datamodels: {yml_datamodels}")
            #print("ERROR")
            yaml_update_required = True
            #input("waiting...\n")
    '''

    toks = get_tokens(search)
    #print(defined_datamodels)
    #print(toks)
    #dictPrint(defined_datamodels)
    
    #For each token (submodel.field) found in the search field, make sure that it is included in the 
    # required_fields portion of the YAML.
    #Required fields in a datamodel should be in the format model.submodel.fieldname to be more explicit.
    #If a field is declared in required_fields that does not have a dot and exists in the raw search, then keep it.
    #If a field is declared in required_fields that does not have a dot and does not exit in the raw search, then remove it.
    
    #Remove all the datamodels and datamodel.submodels from toks.
    toks_without_datamodels = set()
    datamodels_in_use = dict()
    for tok in toks:
        try:
            model,submodel = tok.split(".")
        except Exception:
            raise Exception(f"Did not find 2 . in {tok}")
        
        if model in defined_datamodels and submodel in defined_datamodels[model]:
            #print(f"Found {tok} in defined datamodels!")
            if model not in datamodels_in_use:
                datamodels_in_use[model] = {}
            
            datamodels_in_use[model][submodel] = defined_datamodels[model][submodel]
        else:
            toks_without_datamodels.add((model,submodel))
    

    #dictPrint(datamodels_in_use.keys())
    #dictPrint(toks_without_datamodels)


    fully_qualified_field_dicts = {}
    #locate the field in the declared models
    for submodel, fieldname in toks_without_datamodels:
        #print(f"{submodel}.{fieldname}")
        found = False
        for model in datamodels_in_use:
            dm = datamodels_in_use[model]
            #dictPrint(dm)
            if submodel in dm and fieldname in dm[submodel]:
                fully_qualified_field_dicts[f"{model}.{submodel}.{fieldname}"] = dm[submodel][fieldname]
                found=True
                break
        #If we got here, then we didn't find the fieldname in any of the models! This is bad.
        if found == False:
            print(f"Failed to find {submodel}.{fieldname} in the datamodles {datamodels_in_use.keys()} for {filename}")

        


    if yaml_update_required:
        '''
        print(f"\nMismatch between datamodel(s) used in search and declared datamodel(s)\n"\
              f"\tFilename                        : {filename}\n"\
              f"\tDisjoint Members                : {disjoint_members if len(disjoint_members) > 0 else '{}'}\n"\
              f"\tdatamodels extracted from search: {datamodels_from_search if len(datamodels_from_search) > 0 else '{}'}\n"\
              f"\tdatamodels declared in YAML     : {datamodels_from_datamodel_field if len(datamodels_from_datamodel_field) > 0 else '{}'}\n"\
              f"\tUpdating the datamodels field in the YAML to contain datamodels extracted from search\n")
        '''
        yaml_fields_to_update['datamodel'] = datamodels_from_search


    

    #print(datamodels)
    #print(yml_datamodels)
    #input("waiting...")
    return yaml_fields_to_update


def clean_folder(directory:str, defined_datamodels:dict):
    files = glob.glob(os.path.join(directory,"*"))
    files = [file for file in files if not os.path.basename(file).startswith("ssa___")]
    #print(f"Processing folder {directory} with {len(files)} files")
    failure_count = 0
    error_files = []
    for filename in files:
        try:
            with open(filename,"r") as cfg:
                parsed = yaml.safe_load(cfg)
            
            if "search" not in parsed:
                print(f"Failed to find ['search'] in {filename}")
                failure_count += 1
                continue
            elif "tags" not in parsed:
                print(f"Failed to find ['tags'] {filename}")
                failure_count += 1
                continue
            elif "required_fields" not in parsed["tags"]:
                print(f"Failed to find ['tags']['required_fields'] in {filename}")
                failure_count += 1
                continue
            elif "datamodel" not in parsed:
                print(f"Failed to find ['datamodel'] in {filename}")
                failure_count += 1
                continue
            
            required_fields_from_yaml = set(parsed['tags']['required_fields'])
            fields_to_update = update_required_fields_for_yaml(filename, parsed["search"], set(parsed["tags"]["required_fields"]), set(parsed["datamodel"]), defined_datamodels)
            #print(fields_to_update)



        except yaml.YAMLError as e:
            print(e)
    
    
    print("Errors:%d %s"%(len(error_files), "\n\t".join(error_files)))
    print(f"The number of failures   : {failure_count}")
    print(f"The total number of files: {len(files)}")
    return        


def clean():
    datamodel_directory = sys.argv[1]
    defined_datamodels = load_datamodels_from_directory(datamodel_directory)

    #sys.exit(0)
    folders = sys.argv[2:]
    for folder in folders:
        clean_folder(folder, defined_datamodels)

    pass


if __name__ == "__main__":
    clean()