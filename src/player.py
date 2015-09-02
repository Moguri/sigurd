from __future__ import division

import json
import os
import collections

from direct.actor.Actor import Actor
from direct.showbase.DirectObject import DirectObject
import panda3d.core as p3d

import ecs
import effects


def clamp(value, lower, upper):
    return max(min(value, upper), lower)


class NodePathComponent(ecs.Component):
    __slots__ = [
        'nodepath',
        '_modelpath'
    ]

    typeid = 'NODEPATH'

    def __init__(self, modelpath=None):
        super().__init__()
        self.synchronize = True
        self._modelpath = modelpath if modelpath else ''
        if modelpath is not None:
            self.nodepath = base.loader.loadModel(modelpath)
        else:
            self.nodepath = p3d.NodePath(p3d.PandaNode('node'))

    def __del__(self):
        super().__del__()
        self.nodepath.remove_node()

    def serialize(self):
        d = super().serialize()
        d['modelpath'] = self._modelpath
        d['position'] = list(self.nodepath.get_pos())
        d['rotation'] = list(self.nodepath.get_hpr())

        return d

    def update(self, cdata):
        self.nodepath.set_pos(p3d.LVector3(*cdata['position']))
        self.nodepath.set_hpr(p3d.LVector3(*cdata['rotation']))
        self.nodepath.reparent_to(base.ecsmanager.space.get_component('NODEPATH').nodepath)


class WeaponComponent(ecs.UniqueComponent):
    __slots__ = [
        'name',
        'actor',
        'range',
        'has_hit',
    ]
    typeid = 'WEAPON'

    def __init__(self, name=''):
        super().__init__()
        self.name = name
        self.actor = None
        self.range = 1.0
        self.has_hit = False
        self.synchronize = True

    def __del__(self):
        super().__del__()
        self.actor.remove_node()

    def serialize(self):
        d = super().serialize()
        d['name'] = self.name
        d['anim_name'] = self.actor.getCurrentAnim()
        d['anim_frame'] = self.actor.getCurrentFrame(d['anim_name'])
        return d

    def update(self, cdata):
        self.name = cdata['name']
        if self.actor:
            self.actor.pose(cdata['anim_name'], cdata['anim_frame'])


class CharacterComponent(ecs.UniqueComponent):
    __slots__ = [
        'speed',
        'movement',
        'heading_delta',
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
        'recoil_duration',
        'recoil_timer',
    ]

    typeid = 'CHARACTER'

    def __init__(self, chassis, mesh=None):
        super().__init__()
        self.movement = p3d.LVector3f(0, 0, 0)
        self.heading_delta = 0
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
                component = getattr(effects, component_data['name'] + 'EffectComponent')(component_data['args'])
                track_entity.add_component(component)
            setattr(self, t, track_entity)

        self.current_health = self.health if self._chassis else None

        self.recoil_duration = 0.35
        self.recoil_timer = self.recoil_duration + 1.0

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


class ActorComponent(ecs.UniqueComponent):
    __slots__ = [
        'name',
        'actor',
        'anim_controls',
    ]
    typeid = 'ACTOR'

    def __init__(self, name=''):
        super().__init__()
        self.synchronize = True
        self.name = name
        self.actor = None
        self.anim_controls = {}

    def __del__(self):
        super().__del__()
        if self.actor:
            self.actor.remove_node()

    def serialize(self):
        d = super().serialize()
        d['name'] = self.name
        d['anim_name'] = self.actor.getCurrentAnim()
        d['anim_frame'] = self.actor.getCurrentFrame(d['anim_name'])
        return d

    def update(self, cdata):
        self.name = cdata['name']
        if self.actor:
            self.actor.pose(cdata['anim_name'], cdata['anim_frame'])


class PlayerComponent(ecs.UniqueComponent):
    __slots__ = [
    ]
    typeid = 'PLAYER'


Attack = collections.namedtuple('Attack', 'damage')


class CharacterSystem(ecs.System):
    component_types = [
        'ACTOR',
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
            self._attack_queues[char.entity.guid] = []

        for comp in components.get('ACTOR', []):
            path = 'models/{}/'.format(comp.name)
            anim_files = [os.path.splitext(f)[0] for f in os.listdir(path) if f.endswith('.egg') and f != 'actor.egg']
            anim_dict = {name: path + name for name in anim_files}
            comp.actor = Actor(path + 'actor', anim_dict)
            np_component = comp.entity.get_component('NODEPATH')
            comp.actor.reparent_to(np_component.nodepath)

    def update(self, dt, components):
        for char in components['CHARACTER']:
            nodepath = char.entity.get_component('NODEPATH').nodepath

            actor = None
            if char.entity.has_component('ACTOR'):
                actor = char.entity.get_component('ACTOR').actor

            if actor:
                actor.disableBlend()
                actor.pose('idle', 0)

            # Position
            char_speed = p3d.LVector3f(char.move_speed / 10000.0, char.move_speed / 10000.0, 0.0)
            if char.movement.length_squared() > 0.0:
                new_pos = nodepath.getMat(base.render).xformVec(char.movement)
                new_pos.normalize()
                new_pos.componentwiseMult(char_speed)
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
                char.recoil_timer = 0.0
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
                        vec_to.componentwiseMult(char_speed)
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

            # Resolve recoil
            if char.recoil_timer < char.recoil_duration:
                char.recoil_timer += dt

                if actor:
                    t = min(char.recoil_timer / char.recoil_duration, 1.0)
                    mid_p = 0.33
                    if t > mid_p:
                        t = (t - mid_p) / (1.0 - mid_p)
                        t = 1.0 - t
                    else:
                        t /= mid_p
                    actor.enableBlend()
                    actor.setControlEffect('idle', 1 - t)
                    actor.setControlEffect('hit', t)
                    actor.pose('idle', 0)
                    actor.pose('hit', 0)


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
            try:
                target = components['PLAYER'][0]
            except IndexError:
                continue

            targetnp = target.entity.get_component('NODEPATH').nodepath

            # Face target
            ainp = aicomp.entity.get_component('NODEPATH')
            look_point = targetnp.get_pos()
            look_point.z = ainp.nodepath.get_pos().z
            ainp.nodepath.look_at(look_point, p3d.LVector3(0, 0, 1))

            # Attack target
            aichar = aicomp.entity.get_component('CHARACTER')
            aichar.action_set.add('ATTACK')
