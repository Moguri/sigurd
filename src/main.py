#!/usr/bin/env python2
import math
import random
import sys

from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
import panda3d.core as p3d

p3d.load_prc_file_data('', 'win-size 1920 1080')
p3d.load_prc_file_data('', 'fullscreen #t')

import ecs
import inputmapper
from player import CharacterComponent, PlayerSystem, PlayerComponent, CharacterSystem, WeaponComponent, EffectSystem
from physics import PhysicsSystem, HitBoxComponent


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

        def run_ecs(task):
            self.ecsmanager.update(0)
            return task.cont
        self.taskMgr.add(run_ecs, 'ECS')

        level = ecs.Entity()
        np_component = NodePathComponent('models/level')
        np_component.nodepath.reparent_to(base.render)
        level.add_component(np_component)
        self.ecsmanager.add_entity(level)

        player = ecs.Entity()
        np_component = NodePathComponent()
        np_component.nodepath.reparent_to(base.render)
        base.camera.reparent_to(np_component.nodepath)
        base.camera.set_pos(0, 0, 1.7)
        base.camLens.set_near(0.1)
        player.add_component(np_component)
        player.add_component(CharacterComponent('melee'))
        player.add_component(PlayerComponent())
        player.add_component(WeaponComponent('katana'))
        self.ecsmanager.add_entity(player)

        # Add some enemies
        for i in range(5):
            enemy = ecs.Entity()
            np_component = NodePathComponent()
            np_component.nodepath.reparent_to(base.render)
            pos = (random.uniform(-7.3, 1.3), random.uniform(0.3, 7.6), 0)
            np_component.nodepath.set_pos(*pos)
            enemy.add_component(np_component)
            enemy.add_component(CharacterComponent('melee', 'demon'))
            enemy.add_component(HitBoxComponent())
            self.ecsmanager.add_entity(enemy)

        self.accept('quit-up', sys.exit)
        self.accept('aspectRatioChanged', self.cb_resize)

    def cb_resize(self):
        vfov = 90
        aspect = self.camLens.get_aspect_ratio()
        hfov = math.degrees(2 * math.atan(math.tan(math.radians(vfov)/2.0) * aspect))
        self.camLens.setFov(hfov, vfov)

if __name__ == '__main__':
    app = Sigurd()
    app.run()
