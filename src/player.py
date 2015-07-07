import json
import os

from direct.actor.Actor import Actor
from direct.showbase.DirectObject import DirectObject
import panda3d.core as p3d

import ecs


def clamp(value, lower, upper):
    return max(min(value, upper), lower)


class WeaponComponent(ecs.Component):
    __slots__ = [
        'name',
        'actor',
    ]
    typeid = 'WEAPON'

    def __init__(self, name):
        self.name = name
        self.actor = None


class CharacterComponent(ecs.Component):
    __slots__ = [
        'speed',
        'movement',
        'heading_delta',
        'actor',
        'mesh_name',
        '_chassis',
        'level',
        'action_set',
    ]

    typeid = 'CHARACTER'

    def __init__(self, chassis, mesh=None):
        self.speed = p3d.LVector3f(0.04, 0.04, 0.0)
        self.movement = p3d.LVector3f(0, 0, 0)
        self.heading_delta = 0
        self.actor = None
        self.mesh_name = mesh

        self.level = 1
        with open(os.path.join('chassis', chassis) + '.json') as f:
            self._chassis = json.load(f)

        self.action_set = set()

    @property
    def health(self):
        return self._chassis['health'] + self._chassis['health_per_lvl'] * self.level - 1

    @property
    def mana(self):
        return self._chassis['mana'] + self._chassis['mana_per_lvl'] * self.level - 1

    @property
    def attack_damage(self):
        return self._chassis['attack_damage'] + self._chassis['attack_damage_per_lvl'] * self.level - 1

    @property
    def ability_power(self):
        return self._chassis['ability_power'] + self._chassis['ability_power_per_lvl'] * self.level - 1

    @property
    def move_speed(self):
        return self._chassis['move_speed'] + self._chassis['move_speed_per_lvl'] * self.level - 1

    @property
    def attack_speed(self):
        return self._chassis['attack_speed'] + self._chassis['attack_speed_per_lvl'] * self.level - 1

    @property
    def armor(self):
        return self._chassis['armor'] + self._chassis['armor_per_lvl'] * self.level - 1

    @property
    def magic_resistance(self):
        return self._chassis['magic_resistance'] + self._chassis['magic_resistance_per_lvl'] * self.level - 1


class PlayerComponent(ecs.Component):
    __slots__ = []
    typeid = 'PLAYER'


class CharacterSystem(ecs.System):
    component_types = [
        'CHARACTER',
        'WEAPON',
    ]

    def init_components(self, dt, components):
        #TODO: Component keys should always be in the dictionary

        for weapon in components.get('WEAPON', []):
            weapon.actor = Actor('models/{}'.format(weapon.name))
            np_component = weapon.entity.get_component('NODEPATH')
            weapon.actor.reparent_to(np_component.nodepath)

        for char in components.get('CHARACTER', []):
            if char.mesh_name:
                char.actor = Actor('models/{}'.format(char.mesh_name))
                np_component = char.entity.get_component('NODEPATH')
                char.actor.reparent_to(np_component.nodepath)

    def update(self, dt, components):
        for char in components['CHARACTER']:
            nodepath = char.entity.get_component('NODEPATH').nodepath

            # Position
            new_pos = nodepath.getMat(base.render).xformVec(char.movement)
            new_pos.normalize()
            new_pos.componentwiseMult(char.speed)
            new_pos += nodepath.get_pos()
            nodepath.set_pos(new_pos)

            # Rotation
            heading = nodepath.get_h() + char.heading_delta
            nodepath.set_h(heading)
            char.heading_delta = 0

            if 'ATTACK' in char.action_set:
                if char.entity.has_component('WEAPON'):
                    weapon = char.entity.get_component('WEAPON').actor
                    if not weapon.getAnimControl('attack').isPlaying():
                        weapon.play('attack', fromFrame=1, toFrame=21)
                char.action_set.remove('ATTACK')


class PlayerSystem(ecs.System, DirectObject):
    component_types = [
        'PLAYER',
    ]

    def __init__(self):
        self.movement = p3d.LVector3f(0, 0, 0)
        self.action_set = set()
        self.camera_pitch = 0
        self.mousex_sensitivity = 25
        self.mousey_sensitivity = 25

        self.accept('w', self.update_movement, ['forward', True])
        self.accept('w-up', self.update_movement, ['forward', False])
        self.accept('s', self.update_movement, ['backward', True])
        self.accept('s-up', self.update_movement, ['backward', False])
        self.accept('a', self.update_movement, ['left', True])
        self.accept('a-up', self.update_movement, ['left', False])
        self.accept('d', self.update_movement, ['right', True])
        self.accept('d-up', self.update_movement, ['right', False])
        self.accept('mouse1', self.attack)

    def attack(self):
        self.action_set.add('ATTACK')

    def update_movement(self, direction, activate):
        move_delta = p3d.LVector3(0, 0, 0)

        if direction == 'forward':
            move_delta.set_y(1)
        elif direction == 'backward':
            move_delta.set_y(-1)
        elif direction == 'left':
            move_delta.set_x(-1)
        elif direction == 'right':
            move_delta.set_x(1)

        if not activate:
            move_delta *= -1

        self.movement += move_delta

    def update(self, dt, components):
        player = list(components['PLAYER'])[0]
        pc = player.entity.get_component('CHARACTER')
        pc.movement = self.movement
        pc.action_set = self.action_set.copy()
        self.action_set.clear()
        if base.mouseWatcherNode.has_mouse():
            mouse = base.mouseWatcherNode.get_mouse()
            halfx = base.win.get_x_size() / 2
            halfy = base.win.get_y_size() / 2
            base.win.move_pointer(0, halfx, halfy)

            self.camera_pitch += mouse.y * self.mousey_sensitivity
            self.camera_pitch = clamp(self.camera_pitch, -75, 75)

            pc.heading_delta += -mouse.x * self.mousex_sensitivity

        base.camera.set_p(self.camera_pitch)
