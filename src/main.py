#!/usr/bin/env python2
from direct.showbase.ShowBase import ShowBase


class Sigurd(ShowBase):
	def __init__(self):
		ShowBase.__init__(self)

		level_np = base.loader.loadModel("models/level")
		level_np.reparent_to(base.render)


if __name__ == '__main__':
	app = Sigurd()
	app.run()