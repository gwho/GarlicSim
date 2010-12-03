# Copyright 2009-2010 Ram Rachum.
# This program is distributed under the LGPL2.1 license.


from __future__ import division

import os
import types
import time
import itertools
import cPickle, pickle

import nose

from garlicsim.general_misc import cute_iter_tools
from garlicsim.general_misc import math_tools
from garlicsim.general_misc import path_tools
from garlicsim.general_misc import import_tools
from garlicsim.general_misc.infinity import Infinity

import garlicsim

from ..shared import MustachedThreadCruncher

FUZZ = 0.0001
'''Fuzziness of floats.'''



def test():
    
    from . import sample_simpacks
    
    # Collecting all the test simpacks:
    simpacks = import_tools.import_all(sample_simpacks).values()
    
    # Making sure that we didn't miss any simpack by counting the number of
    # sub-folders in the `sample_simpacks` folders:
    sample_simpacks_dir = \
        os.path.dirname(sample_simpacks.__file__)
    assert len(path_tools.list_sub_folders(sample_simpacks_dir)) == \
           len(simpacks)
    
    cruncher_types = [
        garlicsim.asynchronous_crunching.crunchers.ThreadCruncher,
        
        # Until multiprocessing shit is solved, this is commented-out:
        #garlicsim.asynchronous_crunching.crunchers.ProcessCruncher
    ]
    
    
    for simpack, cruncher_type in \
        cute_iter_tools.product(simpacks, cruncher_types):
        
        # Making `_settings_for_testing` available:
        import_tools.import_all(simpack)
        
        yield check, simpack, cruncher_type

        
def check(simpack, cruncher_type):
    
    
    my_simpack_grokker = garlicsim.misc.SimpackGrokker(simpack)
    
    assert my_simpack_grokker is garlicsim.misc.SimpackGrokker(simpack)
    # Ensuring caching works.
    
    assert garlicsim.misc.simpack_grokker.get_step_type(
        my_simpack_grokker.default_step_function
    ) == simpack._settings_for_testing.DEFAULT_STEP_FUNCTION_TYPE
    
    step_profile = my_simpack_grokker.build_step_profile()
    deterministic = \
        my_simpack_grokker.settings.DETERMINISM_FUNCTION(step_profile)
    
    state = simpack.State.create_root()
    
    
    project = garlicsim.Project(simpack)
        
    project.crunching_manager.cruncher_type = cruncher_type
    
    assert project.tree.lock._ReadWriteLock__writer is None
    
    root = project.root_this_state(state)
    
    ### Test changing step profile on the fly: ################################
    #                                                                         #
    
    # For simpacks providing more than one step function, we'll test changing
    # between them. This will exercise crunchers' ability to receieve a
    # `CrunchingProfile` and react appropriately.
    if simpack._settings_for_testing.N_STEP_FUNCTIONS >= 2:        
        
        def run_sync_crunchers_until_we_get_at_least_one_node():
            while not project.sync_crunchers():
                time.sleep(0.1)
        
        default_step_function, alternate_step_function = \
            my_simpack_grokker.all_step_functions[:2]
        job = project.begin_crunching(root, Infinity)
        assert job.crunching_profile.step_profile.step_function == \
               default_step_function
        run_sync_crunchers_until_we_get_at_least_one_node()
        (cruncher,) = project.crunching_manager.crunchers.values()
        alternate_step_profile = \
            garlicsim.misc.StepProfile(alternate_step_function)
        job.crunching_profile.step_profile = alternate_step_profile
        # Letting our crunching manager get a new cruncher for our new step
        # profile:
        run_sync_crunchers_until_we_get_at_least_one_node()
        (new_cruncher,) = project.crunching_manager.crunchers.values()
        assert new_cruncher is not cruncher
        last_node_with_default_step_profile = job.node
        assert not last_node_with_default_step_profile.children # It's a leaf
        assert last_node_with_default_step_profile.\
               step_profile.step_function == default_step_function
        # Another `sync_crunchers`:
        run_sync_crunchers_until_we_get_at_least_one_node()
        # And now we have some new nodes with the alternate step profile.
        (first_node_with_alternate_step_profile,) = \
            last_node_with_default_step_profile.children
        path = last_node_with_default_step_profile.make_containing_path()
 
        nodes_with_alternate_step_profile = list(
            path.__iter__(start=first_node_with_alternate_step_profile)
        )
        for node in nodes_with_alternate_step_profile:
            assert node.step_profile == alternate_step_profile
        
        # Deleting jobs so the crunchers will stop:
        del project.crunching_manager.jobs[:]
        project.sync_crunchers()
        assert not project.crunching_manager.jobs
        assert not project.crunching_manager.crunchers
        
        
        
    
    #                                                                         #
    ### Finished testing changing step profile on the fly. ####################
    
    ### Testing cruncher type switching: ######################################
    #                                                                         #
    
    job_1 = project.begin_crunching(root, clock_buffer=Infinity)
    job_2 = project.begin_crunching(root, clock_buffer=Infinity)
    
    assert len(project.crunching_manager.crunchers) == 0
    assert project.sync_crunchers() == 0
    assert len(project.crunching_manager.crunchers) == 2
    (cruncher_1, cruncher_2) = project.crunching_manager.crunchers.values()
    assert type(cruncher_1) is cruncher_type
    assert type(cruncher_2) is cruncher_type
    
    time.sleep(0.2) # Letting the crunchers start working
    
    project.crunching_manager.cruncher_type = MustachedThreadCruncher
    project.sync_crunchers()
    assert len(project.crunching_manager.crunchers) == 2
    (cruncher_1, cruncher_2) = project.crunching_manager.crunchers.values()
    assert type(cruncher_1) is MustachedThreadCruncher
    assert type(cruncher_2) is MustachedThreadCruncher
    
    project.crunching_manager.cruncher_type = cruncher_type
    project.sync_crunchers()
    assert len(project.crunching_manager.crunchers) == 2
    (cruncher_1, cruncher_2) = project.crunching_manager.crunchers.values()
    assert type(cruncher_1) is cruncher_type
    assert type(cruncher_2) is cruncher_type
    
    # Deleting jobs so the crunchers will stop:
    del project.crunching_manager.jobs[:]
    project.sync_crunchers()
    assert not project.crunching_manager.jobs
    assert not project.crunching_manager.crunchers
    
    #                                                                         #
    ### Finished testing cruncher type switching. #############################
    
    
    