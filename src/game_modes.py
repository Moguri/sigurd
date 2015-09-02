import random

from direct.showbase.DirectObject import DirectObject

import network
from player import *
from physics import HitBoxComponent


class GameMode(object):
    def start_game(self):
        pass

    def end_game(self):
        pass

    def is_game_over(self):
        pass

class ClassicGameMode(GameMode, DirectObject):
    def __init__(self):
        self.player_id = None
        self.player = None
        self.action_set = set()
        self.movement = p3d.LVector3f(0, 0, 0)

        self.camera_pivot = p3d.LVector3f(0, 0, 1.3)
        self.camera_offset = p3d.LVector3f(0, 0.1, 0.17)
        self.camera_pitch = 0
        self.mousex_sensitivity = 25
        self.mousey_sensitivity = 25

        def update_movement(direction, activate):
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
        self.accept('move-forward', update_movement, ['forward', True])
        self.accept('move-forward-up', update_movement, ['forward', False])
        self.accept('move-backward', update_movement, ['backward', True])
        self.accept('move-backward-up', update_movement, ['backward', False])
        self.accept('move-left', update_movement, ['left', True])
        self.accept('move-left-up', update_movement, ['left', False])
        self.accept('move-right', update_movement, ['right', True])
        self.accept('move-right-up', update_movement, ['right', False])
        self.accept('attack', self.action_set.add, ['ATTACK'])
        self.accept('track-one', self.action_set.add, ['TRACK_ONE'])
        self.accept('track-two', self.action_set.add, ['TRACK_TWO'])
        self.accept('track-three', self.action_set.add, ['TRACK_THREE'])
        self.accept('track-four', self.action_set.add, ['TRACK_FOUR'])
        self.accept('abort', self.action_set.add, ['ABORT_START'])
        self.accept('abort-up', self.action_set.add, ['ABORT_END'])

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

    def start_game(self):
        base.ecsmanager.space = ecs.Entity(None)
        base.ecsmanager.space.add_component(NodePathComponent())
        spacenp = base.ecsmanager.space.get_component('NODEPATH').nodepath
        spacenp.reparent_to(base.render)

        level = base.ecsmanager.create_entity()
        np_component = NodePathComponent('models/new_level')
        np_component.nodepath.reparent_to(spacenp)
        level.add_component(np_component)

        if base.network_manager.netrole == 'CLIENT':
            base.network_manager.broadcast(network.MessageTypes.register_player, {})

        # Add some enemies
        if base.network_manager.netrole == 'SERVER':
            enemy_types = ('melee', 'ranged')
            for i in range(2):
                enemy = base.ecsmanager.create_entity()
                base.network_manager.register_entity(enemy)
                np_component = NodePathComponent()
                np_component.nodepath.reparent_to(spacenp)
                pos = (random.uniform(-6.5, 6.5), random.uniform(0.3, 7.6), 0)
                np_component.nodepath.set_pos(*pos)
                enemy.add_component(np_component)
                enemy.add_component(CharacterComponent('melee', enemy_types[i]))
                enemy.add_component(ActorComponent(enemy_types[i]))
                enemy.add_component(HitBoxComponent())
                enemy.add_component(WeaponComponent('katana'))
                enemy.add_component(AiComponent())

    def update(self, dt):
        if self.player:
            heading_delta = 0
            if base.mouseWatcherNode.has_mouse():
                mouse = base.mouseWatcherNode.get_mouse()
                halfx = base.win.get_x_size() // 2
                halfy = base.win.get_y_size() // 2
                base.win.move_pointer(0, halfx, halfy)

                self.camera_pitch += mouse.y * self.mousey_sensitivity
                self.camera_pitch = clamp(self.camera_pitch, -70, 60)

                heading_delta = -mouse.x * self.mousex_sensitivity

            camera_mat = p3d.LMatrix4f().translate_mat(self.camera_offset)
            rot_mat = p3d.LMatrix4f().rotate_mat(self.camera_pitch, p3d.LVector3f(1, 0, 0))
            trans_mat = p3d.LMatrix4f().translate_mat(self.camera_pivot)

            camera_mat = camera_mat * rot_mat * trans_mat
            base.camera.set_mat(camera_mat)

            base.network_manager.broadcast(network.MessageTypes.player_input, {
                'netid': self.player.netid,
                'heading_delta': heading_delta,
                'movement_x': int(self.movement.get_x()),
                'movement_y': int(self.movement.get_y()),
                'action_set': ','.join(self.action_set),
            })
            self.action_set.clear()

        elif self.player_id is not None:
            player_entity = [entity for entity in base.ecsmanager.entities if entity.netid == self.player_id]
            if player_entity:
                player_entity = player_entity[0]
                np_component = player_entity.get_component('NODEPATH')
                base.camera.reparent_to(np_component.nodepath)
                base.camera.set_pos(0, 0, 1.7)
                base.camLens.set_near(0.05)
                base.camLens.set_far(100)

                self.player = player_entity

    def handle_net_message(self, connection, msgid, data):
        if base.network_manager.netrole == 'SERVER':
            if msgid == network.MessageTypes.register_player:
                print("Create player")
                spacenp = base.ecsmanager.space.get_component('NODEPATH').nodepath
                player = base.ecsmanager.create_entity()
                base.network_manager.register_entity(player)
                np_component = NodePathComponent()
                np_component.nodepath.reparent_to(spacenp)
                player.add_component(np_component)
                player.add_component(CharacterComponent('melee'))
                player.add_component(PlayerComponent())
                player.add_component(WeaponComponent('katana'))
                player.add_component(HitBoxComponent())

                base.network_manager.send_to(connection, network.MessageTypes.player_id, {
                    'netid': player.netid,
                })
            elif msgid == network.MessageTypes.player_input:
                player_entity = [entity for entity in base.ecsmanager.entities if entity.netid == data['netid']]
                if player_entity:
                    pc = player_entity[0].get_component('CHARACTER')
                    pc.heading_delta += data['heading_delta']
                    pc.movement = p3d.LVector3(data['movement_x'], data['movement_y'], 0)
                    pc.action_set |= set(data['action_set'].split(','))
        else:
            if msgid == network.MessageTypes.player_id:
                print("Player ID is", data['netid'])
                self.player_id = data['netid']

    def end_game(self):
        base.ecsmanager.remove_space()
        #base.render.ls()

    def is_game_over(self):
        return False #len([i for i in base.ecsmanager.entities if i.has_component('AI')]) == 0
