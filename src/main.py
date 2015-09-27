#!/usr/bin/env python
import math
import sys
import os
import subprocess
import time
import atexit

from direct.showbase.ShowBase import ShowBase
import panda3d.core as p3d

p3d.load_prc_file('config/engine.prc')
if os.path.exists(os.path.join('config', 'user.prc')):
    p3d.load_prc_file('config/user.prc')

if 'server' in sys.argv:
    p3d.load_prc_file_data('', 'window-type none')

import inputmapper
import game_modes
import network
from player import *
from effects import EffectSystem
from physics import PhysicsSystem


class Sigurd(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        self.render.set_shader_auto()
        light = p3d.DirectionalLight('sun')
        light.set_color(p3d.VBase4(1.0, 0.94, 0.84, 1.0))
        light_np = self.render.attach_new_node(light)
        light_np.set_hpr(p3d.VBase3(0, -45, 0))
        self.render.set_light(light_np)

        light = p3d.DirectionalLight('indirect')
        light.set_color(p3d.VBase4(0.15, 0.15, 0.15, 1.0))
        light_np = self.render.attach_new_node(light)
        light_np.set_hpr(p3d.VBase3(0, 45, 0))
        self.render.set_light(light_np)

        if base.win:
            wp = p3d.WindowProperties()
            wp.set_cursor_hidden(True)
            wp.set_mouse_mode(p3d.WindowProperties.MRelative)
            base.win.requestProperties(wp)
            self.disableMouse()

        self.inputmapper = inputmapper.InputMapper('input.conf')

        self.ecsmanager = ecs.ECSManager()
        self.ecsmanager.add_system(CharacterSystem())
        self.ecsmanager.add_system(PhysicsSystem())
        self.ecsmanager.add_system(EffectSystem())
        self.ecsmanager.add_system(AiSystem())

        port = int(sys.argv[2]) if len(sys.argv) > 2 else 9999
        host = sys.argv[3] if len(sys.argv) > 3 else 'localhost'
        if len(sys.argv) == 1 or sys.argv[1] == 'stand-alone':
            is_server = False
            proc = subprocess.Popen([sys.argv[0], 'server', str(port), str(host)])
            def kill_server():
                if proc:
                    print('Terminating stand-alone server')
                    proc.terminate()
            atexit.register(kill_server)
            time.sleep(1)
        elif sys.argv[1] == 'server':
            is_server = True
        elif sys.argv[1] == 'client':
            is_server = False
        else:
            raise RuntimeError('Unrecognized mode: {}'.format(sys.argv[1]))

        self.network_manager = network.NetworkManager(self.ecsmanager, network.PandaTransportLayer, is_server)
        if is_server:
            self.network_manager.start_server(port)
        else:
            self.network_manager.start_client(host, port)

        self.game_mode = game_modes.ClassicGameMode()

        def run_ecs(task):
            self.ecsmanager.update(globalClock.get_dt())
            if self.game_mode.is_game_over():
                print("Game over, restarting")
                messenger.send('restart-game')
            return task.cont
        self.taskMgr.add(run_ecs, 'ECS')

        def run_net(task):
            self.network_manager.update(globalClock.get_dt())
            return task.cont
        self.taskMgr.add(run_net, 'Network')

        def run_gamemode(task):
            self.game_mode.update(globalClock.get_dt())
            return task.cont
        self.taskMgr.add(run_gamemode, 'Game Mode')

        def restart_game():
            self.game_mode.end_game()
            self.game_mode.start_game()

        restart_game()

        self.accept('restart-game', restart_game)
        self.accept('quit-up', sys.exit)
        self.accept('aspectRatioChanged', self.cb_resize)

    def cb_resize(self):
        vfov = 70
        aspect = self.camLens.get_aspect_ratio()
        hfov = math.degrees(2 * math.atan(math.tan(math.radians(vfov)/2.0) * aspect))
        self.camLens.setFov(hfov, vfov)

if __name__ == '__main__':
    app = Sigurd()
    app.run()
