#!/usr/bin/env python2
import math
import sys
import os

from direct.showbase.ShowBase import ShowBase
import panda3d.core as p3d

p3d.load_prc_file('config/engine.prc')
if os.path.exists(os.path.join('config', 'user.prc')):
    p3d.load_prc_file('config/user.prc')

import ecs
import inputmapper
import game_modes
from player import *
from physics import PhysicsSystem


class Sigurd(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        self.render.set_shader_auto()
        light = p3d.DirectionalLight('sun')
        light.set_color(p3d.VBase4(1.0, 0.94, 0.84, 1.0))
        light_np = self.render.attach_new_node(light)
        light_np.set_hpr(p3d.VBase3(-135.0, -45.0, 0.0))
        self.render.set_light(light_np)

        wp = p3d.WindowProperties()
        wp.set_cursor_hidden(True)
        wp.set_mouse_mode(p3d.WindowProperties.MRelative)
        base.win.requestProperties(wp)
        self.disableMouse()

        self.inputmapper = inputmapper.InputMapper('input.conf')

        self.ecsmanager = ecs.ECSManager()
        self.ecsmanager.add_system(PlayerSystem())
        self.ecsmanager.add_system(CharacterSystem())
        self.ecsmanager.add_system(PhysicsSystem())
        self.ecsmanager.add_system(EffectSystem())
        self.ecsmanager.add_system(AiSystem())

        self.game_mode = game_modes.ClassicGameMode()

        def run_ecs(task):
            self.ecsmanager.update(0)
            if self.game_mode.is_game_over():
                print("Game over, restarting")
                messenger.send('restart-game')
            return task.cont
        self.taskMgr.add(run_ecs, 'ECS')

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
