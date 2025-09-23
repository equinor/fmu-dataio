from fmu.dataio.load.load_standard_results import (
    fluid_contact_surfaces_loader,
    load_inplace_volumes,
    load_structure_depth_fault_surfaces,
    load_structure_depth_surfaces,
)

my_case_id = "250a65b6-257a-4e47-b720-aebd535c5eb8"
ensemble_name = "iter-0"
realization_id = 0
test_save_path = "./test_only"
loaders = {
    "fluid_contact_surfaces_loader": fluid_contact_surfaces_loader,
    "load_inplace_volumes": load_inplace_volumes,
    "load_structure_depth_fault_surfaces": load_structure_depth_fault_surfaces,
    "load_structure_depth_surfaces": load_structure_depth_surfaces,
}

for selected_loader in loaders:
    print()
    print("*************** Setting up loader ***************")
    print()
    loader = loaders[selected_loader](my_case_id, ensemble_name)

    print()
    print("*************** Getting realization ***************")
    print()

    # Get all structure depth fault surfaces objects for a given realization
    objects = loader.get_realization(realization_id)

    print()
    print("*************** Saving realization ***************")
    print()

    # Save the structure depth fault surfaces objects for a given realization
    object_paths = loader.save_realization(realization_id, test_save_path)

    print()
    print("*************** Done ***************")
    print()
