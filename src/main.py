#!/usr/bin/env python2
import math
import sys

from direct.showbase.ShowBase import ShowBase
import panda3d.core as p3d

import ecs
from player import PlayerController

class NodePathComponent(ecs.Component):
    __slots__ = [
        "nodepath",
    ]

    def __init__(self, modelpath=None):
        if modelpath is not None:
            self.nodepath = base.loader.loadModel(modelpath)
        else:
            self.nodepath = p3d.NodePath(p3d.PandaNode('node'))


class Sigurd(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.disableMouse()
    
        self.ecsmanager = ecs.ECSManager()
        def run_ecs(task):
            self.ecsmanager.update(0)
            task.cont
        self.taskMgr.add(run_ecs, 'ECS')

        level = ecs.Entity()
        np_component = NodePathComponent('models/level')
        np_component.nodepath.reparent_to(base.render)
        self.ecsmanager.add_entity(level)

        PlayerController(self.camera)

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
