#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Here workfunctions and normal functions using aiida-stuff (typically used 
within workfunctions) are collected.
"""

from aiida.common.exceptions import InputValidationError
from aiida.work import workfunction as wf
from aiida.orm import DataFactory
from aiida_kkr.tools.kkr_params import kkrparams

#define aiida structures from DataFactory of aiida
ParameterData = DataFactory('parameter')

@wf
def update_params_wf(parameternode, updatenode):
    """
    Work function to update a KKR input parameter node.
    Stores new node in database and creates a link from old parameter node to new node
    Returns updated parameter node using update_params function

    :note: Input nodes need to be valid aiida ParameterData objects.
    
    :param parameternode: Input aiida ParameterData node cotaining KKR specific parameters
    :param updatenode: Input aiida ParameterData node containing a dictionary with the parameters that are supposed to be changed.
    
    :note: If 'nodename' is contained in dict of updatenode the string corresponding to this key will be used as nodename for the new node. Otherwise a default name is used
    :note: Similar for 'nodedesc' which gives new node a description
        
    :example: updated_params = ParameterData(dict={'nodename': 'my_changed_name', 'nodedesc': 'My description text', 'EMIN': -1, 'RMAX': 10.})
              new_params_node = update_params_wf(input_node, updated_params)
    """
    updatenode_dict = updatenode.get_dict()
    if 'nodename' in updatenode_dict.keys():
        # take nodename out of dict (should only contain valid KKR parameter)
        nodename = updatenode_dict.pop('nodename')
    else:
        nodename = None
    if 'nodedesc' in updatenode_dict.keys():
        # take nodename out of dict (should only contain valid KKR parameter later on)
        nodedesc = updatenode_dict.pop('nodedesc')
    else:
        nodedesc = None
    
    # do nothing if updatenode is empty
    if len(updatenode_dict.keys())==0:
        print('Input node is empty, do nothing!')
        raise InputValidationError('Nothing to store in input') 
    # 
    new_parameternode = update_params(parameternode, nodename=nodename, 
                                      nodedesc=nodedesc, **updatenode_dict)
    return new_parameternode
    
        
def update_params(node, nodename=None, nodedesc=None, **kwargs):
    """
    Update parameter node given with the values given as kwargs.
    Returns new node.
    
    :param node: Input parameter node (needs to be valid KKR input parameter node).
    :param **kwargs: Input keys with values as in kkrparams.
    :param linkname: Input linkname string. Give link from old to new node a name . 
                     If no linkname is given linkname defaults to 'updated parameters'
                     
    :return: parameter node
    
    :example usage: OutputNode = KkrCalculation.update_params(InputNode, EMIN=-1, NSTEPS=30)
    
    :note: Keys are set as in kkrparams class. Check documentation of kkrparams for further information.
    :note: By default nodename is 'updated KKR parameters' and description contains list of changed 
    """    
    # check if node is a valid KKR parameters node
    if not isinstance(node, ParameterData):
        print('Input node is not a valid ParameterData node')
        raise InputValidationError('update_params needs valid parameter node as input')
    
    #initialize temporary kkrparams instance containing all possible KKR parameters
    params = kkrparams()
    
    # extract input dict from node
    inp_params = node.get_dict()
    
    # check if input dict contains only values for KKR parameters
    for key in inp_params:
        if key not in params.values.keys():
            print('Input node contains unvalid key "{}"'.format(key))
            raise InputValidationError('unvalid key "{}" in input parameter node'.format(key))
    
    # copy values from input node
    for key in inp_params:
        value = inp_params[key]
        params.set_value(key, value, silent=True)
            
    # to keep track of changed values:
    changed_params = {}
    
    # check if values are given as **kwargs (otherwise return input node)
    if len(kwargs)==0:
        print('No additional input keys given, return input node')
        return node
    else:
        for key in kwargs:
            if kwargs[key] != inp_params[key]:
                params.set_value(key, kwargs[key], silent=True)
                changed_params[key] = kwargs[key]
                
    if len(changed_params.keys())==0:
        print('No keys have been changed, return input node')
        return node
            
    # set linkname with input or default value
    if nodename is None or type(nodename) is not str:
        nodename = 'updated KKR parameters'
    if nodedesc is None or type(nodedesc) is not str:
        nodedesc = 'changed parameters: {}'.format(changed_params)
        
        
    # create new node
    ParaNode = ParameterData(dict=params.values)
    ParaNode.label = nodename
    ParaNode.description = nodedesc
    
    return ParaNode

#TODO implment VCA functionality
# maybe one starts from a calculation closest to the VCA case and slowly 
# increase ZATOM which violates the _do_never_modify rule in KKR calculation
# this should then create a new structure and modify the old potential accordingly
# general rule: Nover destroy the data provenance!!!
@wf
def prepare_VCA_structure_wf():
    pass

def prepare_VCA_structure():
    pass


#TODO implement 2D input helper
# a helper workfunction would be nice to create the vacuum region etc. for 2D calculation
@wf
def prepare_2Dcalc_wf():
    pass

def prepare_2Dcalc():
    pass


def test_and_get_codenode(codenode, expected_code_type, use_exceptions=False):
    """
    Pass a code node and an expected code (plugin) type. Check that the
    code exists, is unique, and return the Code object.

    :param codenode: the name of the code to load (in the form label@machine)
    :param expected_code_type: a string with the plugin that is expected to
      be loaded. In case no plugins exist with the given name, show all existing
      plugins of that type
    :param use_exceptions: if True, raise a ValueError exception instead of
      calling sys.exit(1)
    :return: a Code object
    
    Example usage (from kkr_scf workchain):
        if 'voronoi' in inputs:
            try:
                test_and_get_codenode(inputs.voronoi, 'kkr.voro', use_exceptions=True)
            except ValueError:
                error = ("The code you provided for voronoi  does not "
                         "use the plugin kkr.voro")
                self.control_end_wc(error)
    """
    import sys
    from aiida.common.exceptions import NotExistent
    from aiida.orm import Code


    try:
        if codenode is None:
            raise ValueError
        code = codenode
        if code.get_input_plugin_name() != expected_code_type:
            raise ValueError
    except (NotExistent, ValueError):
        from aiida.orm.querybuilder import QueryBuilder
        qb = QueryBuilder()
        qb.append(Code,
                  filters={'attributes.input_plugin':
                               {'==': expected_code_type}},
                  project='*')

        valid_code_labels = ["{}@{}".format(c.label, c.get_computer().name)
                             for [c] in qb.all()]

        if valid_code_labels:
            msg = ("Pass as further parameter a valid code label.\n"
                   "Valid labels with a {} executable are:\n".format(
                expected_code_type))
            msg += "\n".join("* {}".format(l) for l in valid_code_labels)

            if use_exceptions:
                raise ValueError(msg)
            else:
                print >> sys.stderr, msg
                sys.exit(1)
        else:
            msg = ("Code not valid, and no valid codes for {}.\n"
                   "Configure at least one first using\n"
                   "    verdi code setup".format(
                expected_code_type))
            if use_exceptions:
                raise ValueError(msg)
            else:
                print >> sys.stderr, msg
                sys.exit(1)

    return code

    
def get_inputs_kkr(code, remote, options, label='', description='', parameters=None, serial=False):
    """
    Get the input for a voronoi calc.
    Wrapper for VoronoiProcess setting structure, code, options, label, description etc.
    """
    from aiida_kkr.calculations.kkr import KkrCalculation
    KkrProcess = KkrCalculation.process()
    inputs = KkrProcess.get_inputs_template()
    if remote:
        inputs.parent_folder = remote
    if code:
        inputs.code = code
    if parameters:
        inputs.parameters = parameters
    for key, val in options.iteritems():
        if val==None:
            continue
        else:
            inputs._options[key] = val

    if description:
        inputs['_description'] = description
    else:
        inputs['_description'] = ''
    if label:
        inputs['_label'] = label
    else:
        inputs['_label'] = ''

    if serial:
        inputs._options.withmpi = False # for now
        inputs._options.resources = {"num_machines": 1}


    '''
    options = {
    "max_wallclock_seconds": int,
    "resources": dict,
    "custom_scheduler_commands": unicode,
    "queue_name": basestring,
    "computer": Computer,
    "withmpi": bool,
    "mpirun_extra_params": Any(list, tuple),
    "import_sys_environment": bool,
    "environment_variables": dict,
    "priority": unicode,
    "max_memory_kb": int,
    "prepend_text": unicode,
    "append_text": unicode}
    '''
    return inputs


def get_inputs_voronoi(structure, voronoicode, options, label='', description='', params=None, serial=True):
    """
    Get the input for a voronoi calc.
    Wrapper for VoronoiProcess setting structure, code, options, label, description etc.
    """
    from aiida_kkr.calculations.voro import VoronoiCalculation
    VoronoiProcess = VoronoiCalculation.process()
    inputs = VoronoiProcess.get_inputs_template()

    if structure:
        inputs.structure = structure
    if voronoicode:
        inputs.code = voronoicode
    if params:
        inputs.parameters = params
    for key, val in options.iteritems():
        if val==None:
            #leave them out, otherwise the dict schema won't validate
            continue
        else:
            inputs._options[key] = val

    if description:
        inputs['_description'] = description
    else:
        inputs['_description'] = ''

    if label:
        inputs['_label'] = label
    else:
        inputs['_label'] = ''

    if serial:
        inputs._options.withmpi = False # for now
        inputs._options.resources = {"num_machines": 1}

    return inputs

def get_parent_paranode(remote_data):
    """
    Return the input parameter of the parent calulation giving the remote_data node
    """
    inp_para = remote_data.inp.remote_folder.inp.parameters
    return inp_para


def generate_inputcard_from_structure(parameters, structure, input_filename, parent_calc=None, shapes=None, isvoronoi=False):
    """
    Takes information from parameter and structure data and writes input file 'input_filename'
    
    :param parameters: input parameters node containing KKR-related input parameter
    :param structure: input structure node containing lattice information
    :param input_filename: input filename, typically called 'inputcard'
    
    
    optional arguments
    :param parent_calc: input parent calculation node used to determine if EMIN 
                        parameter is automatically overwritten (from voronoi output)
                        or not
    :param shapes: input shapes array (set automatically by 
                   aiida_kkr.calculations.Kkrcaluation and shall not be overwritten)
    
    
    :note: assumes valid structure and parameters, i.e. for 2D case all necessary 
           information has to be given. This is checked with function 
           'check_2D_input' called in aiida_kkr.calculations.Kkrcaluation
    """
    
    from aiida.common.constants import elements as PeriodicTableElements
    from numpy import array
    from aiida_kkr.tools.kkr_params import kkrparams
    from aiida_kkr.tools.common_functions import get_Ang2aBohr, get_alat_from_bravais
    from aiida_kkr.calculations.voro import VoronoiCalculation
    
    #list of globally used constants
    a_to_bohr = get_Ang2aBohr()


    # Get the connection between coordination number and element symbol
    # maybe do in a differnt way
    
    _atomic_numbers = {data['symbol']: num for num,
                    data in PeriodicTableElements.iteritems()}
    
    # KKR wants units in bohr
    bravais = array(structure.cell)*a_to_bohr
    alat = get_alat_from_bravais(bravais, is3D=structure.pbc[2])
    bravais = bravais/alat
    
    sites = structure.sites
    naez = len(sites)
    positions = []
    charges = []
    weights = [] # for CPA
    isitelist = [] # counter sites array for CPA
    isite = 0
    for site in sites:
        pos = site.position 
        #TODO maybe convert to rel pos and make sure that type is right for script (array or tuple)
        abspos = array(pos)*a_to_bohr/alat # also in units of alat
        positions.append(abspos)
        isite += 1
        sitekind = structure.get_kind(site.kind_name)
        for ikind in range(len(sitekind.symbols)):
            site_symbol = sitekind.symbols[ikind]
            if not sitekind.has_vacancies():
                charges.append(_atomic_numbers[site_symbol])
            else:
                charges.append(0.0)
            #TODO deal with VCA case
            if sitekind.is_alloy():
                weights.append(sitekind.weights[ikind])
            else:
                weights.append(1.)
            
            isitelist.append(isite)
    
    weights = array(weights)
    isitelist = array(isitelist)
    charges = array(charges)
    positions = array(positions)
        

    ######################################
    # Prepare keywords for kkr from input structure
    
    # get parameter dictionary
    input_dict = parameters.get_dict()
    
    # empty kkrparams instance (contains formatting info etc.)
    if not isvoronoi:
        params = kkrparams()
    else:
        params = kkrparams(params_type='voronoi')
    
    # for KKR calculation set EMIN automatically from parent_calc (ausways in res.emin of voronoi and kkr)
    if ('EMIN' not in input_dict.keys() or input_dict['EMIN'] is None) and parent_calc is not None:
        print('Overwriting EMIN with value from parent calculation')
        if isinstance(parent_calc, VoronoiCalculation):
            emin = parent_calc.res.emin
        else:
            emin = parent_calc.res.energy_contour_group['emin']
        print('Setting emin:',emin, 'is emin None?',emin is None)
        params.set_value('EMIN', emin)
        
    # overwrite keywords with input parameter
    for key in input_dict.keys():
        params.set_value(key, input_dict[key], silent=True)

    # Write input to file (the parameters that are set here are not allowed to be modfied externally)
    params.set_multiple_values(BRAVAIS=bravais, ALATBASIS=alat, NAEZ=naez, 
                               ZATOM=charges, RBASIS=positions, CARTESIAN=True)
    # for CPA case:
    if len(weights)>naez:
        natyp = len(weights)
        params.set_value('NATYP', natyp)
        params.set_value('<CPA-CONC>', weights)
        params.set_value('<SITE>', isitelist)
    else:
        natyp = naez
        
    # write shapes (extracted from voronoi parent automatically in kkr calculation plugin)
    if shapes is not None:
        params.set_value('<SHAPE>', shapes)
        
    # change input values of 2D input to new alat:
    rbl = params.get_value('<RBLEFT>')
    rbr = params.get_value('<RBRIGHT>')
    zper_l = params.get_value('ZPERIODL')
    zper_r = params.get_value('ZPERIODR')
    if rbl is not None: params.set_value('<RBLEFT>', array(rbl)*a_to_bohr/alat)
    if rbr is not None: params.set_value('<RBRIGHT>', array(rbr)*a_to_bohr/alat)
    if zper_l is not None: params.set_value('ZPERIODL', array(zper_l)*a_to_bohr/alat)
    if zper_r is not None: params.set_value('ZPERIODR', array(zper_r)*a_to_bohr/alat)
    
    # write inputfile
    params.fill_keywords_to_inputfile(output=input_filename)
    
    nspin = params.get_value('NSPIN')
    
    newsosol = False
    if 'NEWSOSOL' in params.get_value('RUNOPT'):
        newsosol = True
    
    return natyp, nspin, newsosol
    
    
def check_2Dinput_consistency(structure, parameters):
    """
    Check if structure and parameter data are complete and matching.
    
    :param input: structure, needs to be a valid aiida StructureData node
    :param input: parameters, needs to be valid aiida ParameterData node
    
    returns (False, errormessage) if an inconsistency has been found, otherwise return (True, '2D consistency check complete')
    """
    # default is bulk, get 2D info from structure.pbc info (periodic boundary contitions)
    is2D = False
    if not all(structure.pbc):
        # check periodicity, assumes finite size in z-direction
        if structure.pbc != (True, True, False):
            return (False, "Structure.pbc is neither (True, True, True) for bulk nor (True, True, False) for surface calculation!")
        is2D = True
    
    # check for necessary info in 2D case
    inp_dict = parameters.get_dict()
    set_keys = [i for i in inp_dict.keys() if inp_dict[i] is not None]
    has2Dinfo = True
    for icheck in ['INTERFACE', '<NRBASIS>', '<RBLEFT>', '<RBRIGHT>', 'ZPERIODL', 'ZPERIODR', '<NLBASIS>']:
        if icheck not in set_keys:
            has2Dinfo = False
    if has2Dinfo and not inp_dict['INTERFACE'] and is2D:
        return (False, "'INTERFACE' parameter set to False but structure is 2D")
        
    if has2Dinfo!=is2D:
        return (False, "2D info given in parameters but structure is 3D\nstructure is 2D? {}\ninput has 2D info? {}\nset keys are: {}".format(is2D, has2Dinfo, set_keys))
    
    # if everything is ok:
    return (True, "2D consistency check complete")

