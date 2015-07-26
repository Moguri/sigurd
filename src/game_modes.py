import random

import ecs
from player import *
from physics import HitBoxComponent


class GameMode(object):
    def start_game(self):
        pass

    def end_game(self):
        pass

    def is_game_over(self):
        pass

class ClassicGameMode(GameMode):
    def start_game(self):
        base.ecsmanager.space = ecs.Entity(None)
        base.ecsmanager.space.add_component(NodePathComponent())
        spacenp = base.ecsmanager.space.get_component('NODEPATH').nodepath
        spacenp.reparent_to(base.render)

        level = base.ecsmanager.create_entity()
        np_component = NodePathComponent('models/new_level')
        np_component.nodepath.reparent_to(spacenp)
        level.add_component(np_component)

        player = base.ecsmanager.create_entity()
        np_component = NodePathComponent()
        np_component.nodepath.reparent_to(spacenp)
        base.camera.reparent_to(np_component.nodepath)
        base.camera.set_pos(0, 0, 1.7)
        base.camLens.set_near(0.05)
        base.camLens.set_far(100)
        player.add_component(np_component)
        player.add_component(CharacterComponent('melee'))
        player.add_component(PlayerComponent())
        player.add_component(WeaponComponent('katana'))
        player.add_component(HitBoxComponent())

        # Add some enemies
        enemy_types = ('melee', 'ranged')
        for i in range(2):
            enemy = base.ecsmanager.create_entity()
            np_component = NodePathComponent()
            np_component.nodepath.reparent_to(spacenp)
            pos = (random.uniform(-6.5, 6.5), random.uniform(0.0, 13), 0)
            np_component.nodepath.set_pos(*pos)
            enemy.add_component(np_component)
            enemy.add_component(CharacterComponent('melee'))
            enemy.add_component(ActorComponent(enemy_types[i]))
            enemy.add_component(HitBoxComponent())
            enemy.add_component(WeaponComponent('katana'))
            enemy.add_component(AiComponent())

    def end_game(self):
        base.ecsmanager.remove_space()
        #base.render.ls()

    def is_game_over(self):
        return len([i for i in base.ecsmanager.entities if i.has_component('AI')]) == 0
