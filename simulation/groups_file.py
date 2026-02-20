#!/usr/bin/env python3

#
# groups_file.py
#
# Group file format for the L7R combat simulator.
# A single YAML file gives the groups and the names of the characters in the group.
#

import yaml

from simulation.groups import Group


class GroupsReader:
    def read(self, f, characterd):
        """
        read(path, characterd) -> list of Group
          f (file like object): file like object to access groups.yaml file
          characterd (dict): dictionary of str:Character mappings of names to characters.

        Returns a list of groups of characters.
        The groups are defined in groups.yaml,
        and the characters are defined in other files
        in the same directory.

        The groups.yaml format is like this:

        east:
          control: true
          characters:
          - akodo
          - doji
        west:
          test: true
          characters:
          - bayushi
          - hida
        """
        data = yaml.safe_load(f)
        groups = []
        control_group = None
        # read groups
        for group_name in data.keys():
            groupd = data[group_name]
            # group must have characters
            if "characters" not in groupd.keys():
                raise OSError('Invalid groups file: groups must have a "characters" key with a list of character names')
            # assign characters to group
            characters = []
            character_names = groupd["characters"]
            for character_name in character_names:
                if character_name not in characterd.keys():
                    raise OSError(f"Invalid groups file: character {character_name} was not defined")
                # remove character to prevent double assignment
                character = characterd.pop(character_name)
                characters.append(character)
            group = Group(group_name, characters)
            # determine whether this is control or test group
            if "control" in groupd.keys() and "test" in groupd.keys():
                raise OSError(f"Invalid groups file: group {group_name} is defined as both control and test")
            elif "control" in groupd.keys():
                control_group = group
            elif "test" in groupd.keys():
                pass  # test group identified by absence of 'control'
            # add group
            groups.append(group)
        # must have two groups
        if len(groups) != 2:
            raise OSError("groups.yaml must define two groups")
        # sort groups so control group is first
        groups.sort(key=lambda x: 0 if x == control_group else 1)
        return groups
