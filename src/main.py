#!/usr/bin/env python2
import math
import sys

from direct.showbase.ShowBase import ShowBase
import panda3d.core as p3d

import ecs
from player import CharacterComponent, PlayerSystem, PlayerComponent, CharacterSystem

class NodePathComponent(ecs.Component):
    __slots__ = [
        "nodepath",
    ]

    typeid = 'NODEPATH'

    def __init__(self, modelpath=None):
        if modelpath is not None:
            self.nodepath = base.loader.loadModel(modelpath)
        else:
            self.nodepath = p3d.NodePath(p3d.PandaNode('node'))


class Sigurd(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        wp = p3d.WindowProperties()
        wp.set_cursor_hidden(True)
        wp.set_mouse_mode(p3d.WindowProperties.MRelative)
        base.win.requestProperties(wp)
        self.disableMouse()
    
        self.ecsmanager = ecs.ECSManager()
        self.ecsmanager.add_system(PlayerSystem())
        self.ecsmanager.add_system(CharacterSystem())
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
        player.add_component(np_component)
        player.add_component(CharacterComponent())
        player.add_component(PlayerComponent())
        self.ecsmanager.add_entity(player)

        self.accept('escape-up', sys.exit)
        self.accept('aspectRatioChanged', self.cb_resize)

    def cb_resize(self):
        vfov = 70
        aspect = self.camLens.get_aspect_ratio()
        hfov = math.degrees(2 * math.atan(math.tan(math.radians(vfov)/2.0) * aspect))
        self.camLens.setFov(hfov, vfov)

if __name__ == '__main__':
    app = Sigurd()
    app.run()
