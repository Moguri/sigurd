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


class LevelData(object):
    def __init__(self, level, parent):
        # Load model and setup entity
        self.entity = base.ecsmanager.create_entity()
        np_component = NodePathComponent('models/level2d')
        np_component.nodepath.reparent_to(parent)
        self.entity.add_component(np_component)
        player_start_nodes = np_component.nodepath.find_all_matches('**/playerstart;+h-s+i')

        # Grab start positions
        self.start_positions = []
        for psn in player_start_nodes:
            psn.hide()
            self.start_positions.append(psn.get_pos())
        else:
            print('Warning: No player start, using (0, 0, 0)')

class ClassicGameMode(GameMode, DirectObject):
    def __init__(self):
        self.player_id = None
        self.player = None
        self.action_set = set()
        self.movement = p3d.LVector3f(0, 0, 0)

        self.level_data = None

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

        self.level_data = LevelData('models/level2d', spacenp)

        if base.network_manager.netrole == 'CLIENT':
            base.camera.set_hpr(0, 0, 0)
            base.camera.set_y(-30)
            ortho_lens = p3d.OrthographicLens()
            ortho_lens.set_film_size(35)
            base.cam.node().set_lens(ortho_lens)
            base.network_manager.broadcast(network.MessageTypes.register_player, {})

        # No enemies for now
        # Add some enemies
        #if base.network_manager.netrole == 'SERVER':
        #    enemy_types = ('melee', 'ranged')
        #    for i in range(2):
        #        enemy = base.ecsmanager.create_entity()
        #        base.network_manager.register_entity(enemy)
        #        np_component = NodePathComponent()
        #        np_component.nodepath.reparent_to(spacenp)
        #        pos = (random.uniform(-6.5, 6.5), random.uniform(0.3, 7.6), 0)
        #        np_component.nodepath.set_pos(*pos)
        #        enemy.add_component(np_component)
        #        enemy.add_component(CharacterComponent('melee', enemy_types[i]))
        #        enemy.add_component(ActorComponent(enemy_types[i]))
        #        enemy.add_component(HitBoxComponent())
        #        enemy.add_component(WeaponComponent('katana'))
        #        enemy.add_component(AiComponent())

    def update(self, dt):
        if self.player:
            base.network_manager.broadcast(network.MessageTypes.player_input, {
                'netid': self.player.netid,
                'movement_x': int(self.movement.get_x()),
                'action_set': ','.join(self.action_set),
            })
            self.action_set.clear()

        elif self.player_id is not None:
            player_entity = [entity for entity in base.ecsmanager.entities if entity.netid == self.player_id]
            if player_entity:
                player_entity = player_entity[0]
                np_component = player_entity.get_component('NODEPATH')

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
                player.add_component(ActorComponent('melee'))
                player.add_component(PlayerComponent())
                player.add_component(HitBoxComponent())

                np_component.nodepath.set_pos(random.choice(self.level_data.start_positions))
                np_component.nodepath.set_h(-90)

                base.network_manager.send_to(connection, network.MessageTypes.player_id, {
                    'netid': player.netid,
                })
            elif msgid == network.MessageTypes.player_input:
                player_entity = [entity for entity in base.ecsmanager.entities if entity.netid == data['netid']]
                if player_entity:
                    pc = player_entity[0].get_component('CHARACTER')
                    pc.movement = p3d.LVector3(data['movement_x'], 0, 0)
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
