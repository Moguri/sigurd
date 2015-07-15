from __future__ import division

import json
import os
import collections

from direct.actor.Actor import Actor
from direct.showbase.DirectObject import DirectObject
import panda3d.core as p3d

import ecs


def clamp(value, lower, upper):
    return max(min(value, upper), lower)


class NodePathComponent(ecs.Component):
    __slots__ = [
        'nodepath',
    ]

    typeid = 'NODEPATH'

    def __init__(self, modelpath=None):
        super().__init__()
        if modelpath is not None:
            self.nodepath = base.loader.loadModel(modelpath)
        else:
            self.nodepath = p3d.NodePath(p3d.PandaNode('node'))

    def __del__(self):
        super().__del__()
        self.nodepath.remove_node()


class WeaponComponent(ecs.UniqueComponent):
    __slots__ = [
        'name',
        'actor',
        'range',
        'has_hit',
    ]
    typeid = 'WEAPON'

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.actor = None
        self.range = 1.0
        self.has_hit = False

    def __del__(self):
        super().__del__()
        self.actor.remove_node()


class CharacterComponent(ecs.UniqueComponent):
    __slots__ = [
        'speed',
        'movement',
        'heading_delta',
        'actor',
        'mesh_name',
        '_chassis',
        'level',
        'action_set',
        'attack_move_target',
        'target_entity_guid',
        'track_one',
        'track_two',
        'track_three',
        'track_four',
        'current_health',
    ]

    typeid = 'CHARACTER'

    def __init__(self, chassis, mesh=None):
        super().__init__()
        self.speed = p3d.LVector3f(0.04, 0.04, 0.0)
        self.movement = p3d.LVector3f(0, 0, 0)
        self.heading_delta = 0
        self.actor = None
        self.mesh_name = mesh

        self.level = 1
        with open(os.path.join('chassis', chassis) + '.json') as f:
            self._chassis = json.load(f)

        self.action_set = set()

        for t in ['track_one', 'track_two', 'track_three', 'track_four']:
            with open(os.path.join('tracks', t) + '.json') as f:
                track_data = json.load(f)
            track_entity = base.ecsmanager.create_entity()
            for component_data in track_data['components']:
                component = globals()[component_data['name'] + 'EffectComponent'](component_data['args'])
                track_entity.add_component(component)
            setattr(self, t, track_entity)

        self.current_health = self.health

    def __del__(self):
        super().__del__()
        if self.actor:
            self.actor.remove_node()

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


class PlayerComponent(ecs.UniqueComponent):
    __slots__ = []
    typeid = 'PLAYER'

    def __init__(self):
        super().__init__()


Attack = collections.namedtuple('Attack', 'damage')


class CharacterSystem(ecs.System):
    component_types = [
        'CHARACTER',
        'WEAPON',
    ]

    def __init__(self):
        super().__init__()
        self._attack_queues = {}

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
            self._attack_queues[char.entity.guid] = []

    def update(self, dt, components):
        for char in components['CHARACTER']:
            nodepath = char.entity.get_component('NODEPATH').nodepath

            # Position
            if char.movement.length_squared() > 0.0:
                new_pos = nodepath.getMat(base.render).xformVec(char.movement)
                new_pos.normalize()
                new_pos.componentwiseMult(char.speed)
                new_pos += nodepath.get_pos()
                nodepath.set_pos(new_pos)
                char.action_set.discard('ATTACK_MOVE')

            # Rotation
            heading = nodepath.get_h() + char.heading_delta
            nodepath.set_h(heading)
            char.heading_delta = 0

            # Resolve attacks
            for attack in self._attack_queues[char.entity.guid]:
                char.current_health -= attack.damage
            self._attack_queues[char.entity.guid].clear()

            if 'ATTACK' in char.action_set:
                if base.ecsmanager.has_system('PhysicsSystem'):
                    physics = base.ecsmanager.get_system('PhysicsSystem')
                    to_vec = base.render.get_relative_vector(nodepath, p3d.LVector3f(0, 1, 0))
                    from_pos = nodepath.get_pos() + p3d.LVector3f(0, 0, 0.5)
                    to_pos = from_pos + to_vec * 1000
                    hits = physics.ray_cast(from_pos, to_pos, all_hits=True)
                    if hits:
                        hit = min(hits, key=lambda h: h.t)
                        char.attack_move_target = hit.position
                        char.target_entity_guid = hit.component.entity.guid
                        char.action_set.add('ATTACK_MOVE')

                char.action_set.remove('ATTACK')

            if 'ATTACK_MOVE' in char.action_set:
                if char.entity.has_component('WEAPON'):
                    weapon = char.entity.get_component('WEAPON')

                    vec_to = char.attack_move_target - nodepath.get_pos()
                    distance = vec_to.length()
                    if distance < weapon.range:
                        anim_control = weapon.actor.getAnimControl('attack')
                        if not anim_control.is_playing():
                            if weapon.has_hit:
                                weapon.has_hit = False
                                char.action_set.discard('ATTACK_MOVE')
                            else:
                                weapon.actor.play('attack', fromFrame=1, toFrame=21)

                        if not weapon.has_hit and anim_control.get_frame() >= 18:
                            weapon.has_hit = True
                            self._attack_queues[char.target_entity_guid].append(Attack(1))
                    else:
                        vec_to.normalize()
                        vec_to.componentwiseMult(char.speed)
                        new_pos = nodepath.get_pos() + vec_to
                        nodepath.set_pos(new_pos)

            for track in ['TRACK_ONE', 'TRACK_TWO', 'TRACK_THREE', 'TRACK_FOUR']:
                if track in char.action_set:
                    for component in getattr(char, track.lower()).get_components('EFFECT'):
                        component.cmd_queue.add('ACTIVATE')
                    char.action_set.remove(track)

            # Resolve health and dying
            # TODO make the player invincible for now
            if char.current_health <= 0 and not char.entity.has_component('PLAYER'):
                char.entity.remove_component(char.entity.get_component('PHY_HITBOX'))
                base.ecsmanager.remove_entity(char.entity)


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

        self.accept('move-forward', self.update_movement, ['forward', True])
        self.accept('move-forward-up', self.update_movement, ['forward', False])
        self.accept('move-backward', self.update_movement, ['backward', True])
        self.accept('move-backward-up', self.update_movement, ['backward', False])
        self.accept('move-left', self.update_movement, ['left', True])
        self.accept('move-left-up', self.update_movement, ['left', False])
        self.accept('move-right', self.update_movement, ['right', True])
        self.accept('move-right-up', self.update_movement, ['right', False])
        self.accept('attack', self.add_action, ['ATTACK'])
        self.accept('track-one', self.add_action, ['TRACK_ONE'])
        self.accept('track-two', self.add_action, ['TRACK_TWO'])
        self.accept('track-three', self.add_action, ['TRACK_THREE'])
        self.accept('track-four', self.add_action, ['TRACK_FOUR'])

    def add_action(self, action):
        self.action_set.add(action)

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
        try:
            player = list(components['PLAYER'])[0]
        except IndexError:
            # TODO: for now, let the game still run if the player is missing
            return
        pc = player.entity.get_component('CHARACTER')
        pc.movement = p3d.LVector3(self.movement)
        pc.action_set = pc.action_set.union(self.action_set)
        self.action_set.clear()
        if base.mouseWatcherNode.has_mouse():
            mouse = base.mouseWatcherNode.get_mouse()
            halfx = base.win.get_x_size() // 2
            halfy = base.win.get_y_size() // 2
            base.win.move_pointer(0, halfx, halfy)

            self.camera_pitch += mouse.y * self.mousey_sensitivity
            self.camera_pitch = clamp(self.camera_pitch, -75, 75)

            pc.heading_delta += -mouse.x * self.mousex_sensitivity

        base.camera.set_p(self.camera_pitch)

class EffectComponent(ecs.Component):
    __slots__ = [
        'cmd_queue',
        'effect_type'
    ]
    typeid = 'EFFECT'

    def __init__(self):
        super().__init__()
        self.cmd_queue = set()

class PrintEffectComponent(EffectComponent):
    __slots__ = ['message']
    effect_type = 'PRINT'

    def __init__(self, effect_data):
        super().__init__()
        EffectComponent.__init__(self)
        self.message = effect_data['message']

class EffectSystem(ecs.System):
    __slots__ = []

    component_types = [
        'EFFECT',
    ]

    def update(self, dt, components):
        for component in components['EFFECT']:
            cfunc = component.effect_type.lower() + '_effect'
            if 'ACTIVATE' in component.cmd_queue:
                getattr(self, cfunc)(dt, component)
                component.cmd_queue.remove('ACTIVATE')

    def print_effect(self, dt, component):
        print(component.message)


class AiComponent(ecs.UniqueComponent):
    __slots__ = [

    ]

    typeid = 'AI'


class AiSystem(ecs.System):
    component_types = [
        'PLAYER',
        'AI',
    ]

    def update(self, dt, components):
        for aicomp in components['AI']:
            # Pick target
            target = components['PLAYER'][0]
            targetnp = target.entity.get_component('NODEPATH').nodepath

            # Face target
            ainp = aicomp.entity.get_component('NODEPATH')
            look_point = targetnp.get_pos()
            look_point.z = ainp.nodepath.get_pos().z
            ainp.nodepath.look_at(look_point, p3d.LVector3(0, 0, 1))

            # Attack target
            aichar = aicomp.entity.get_component('CHARACTER')
            aichar.action_set.add('ATTACK')
