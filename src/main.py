from direct.showbase.ShowBase import ShowBase


class Sigurd(ShowBase):
	def __init__(self):
		ShowBase.__init__(self)


if __name__ == '__main__':
	app = Sigurd()
	app.run()