#!/usr/bin/env python

from math import * 
from struct import *
from array import *
import numpy
import sys
import random
import ctypes

from OpenGL import constants
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

# tell OpenGL not to copy arrays that are passed to it
OpenGL.ERROR_ON_COPY = True

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600

CENTERX = WINDOW_WIDTH / 2.0
CENTERY = WINDOW_HEIGHT / 2.0

# mouse sensitivity, higher number means greater sensitivity
MOUSE_SENSITIVITY = 0.2

FOV = 45
zfar_pers = 500.0

# the maze is WIDTH x LENGTH cells
WIDTH = 25
LENGTH = 25

# cells are cubes with this width
CELL_SIZE = 10.0

# the goal cell
GOALX = WIDTH - 1
GOALY = 0

# the cell that the player starts out in
STARTX = 0
STARTY = LENGTH - 1

# wall constants
NORTH = 1
EAST = 2
SOUTH = 4
WEST = 8

ALL_DIRS = NORTH | SOUTH | EAST | WEST

VISITED = 16
HINT = 32

# whether to use textures
do_texturing = False

# whether to do lighting
do_lighting = True

# whether the camera is above the maze
above = False

# whether to perform collision checking
collision_checking = True

# how high above the maze the camera is
birds_eye_height = 0.0

# whether the player has won the game
won = False

give_hints = False

yrot = 0.0
yrot_delta = 5.0

xrot = 0.0
xrot_delta = 5.0

player_xpos = 0.0 #-85.714348
player_zpos = 0.0 #-87.5

ztrans_delta = 0.0
xtrans_delta = 0.0

goal_rot = 0.0
goal_rot_delta = 2.5

timer_repeat = 250

rad_per_deg = pi/180.0

grab_mouse = False

# game start time in ms
start_time = 0

# whether to show elapsed time
show_elapsed = False

elapsed = 0

# whether to show remaining time
show_remaining = False

timer_enabled = False

x1 = -0.5
y1 = -0.5
x2 = 0.5
y2 = 0.5
square_vertices = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
wall_vertices = []
floor_vertices = []

wall_tex_coords = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
floor_tex_coords = [[0.0, 0.0], [WIDTH, 0.0], [WIDTH, LENGTH], [0.0, LENGTH]]

grid_color = [1.0, 1.0, 1.0, 1.0]

light_position = [0.0, 0.0, 0.0, 1.0]
global_ambient = [0.8, 0.8, 0.8, 1.0]
light_diffuse = [1.0, 1.0, 1.0, 1.0]
light_ambient = [1.0, 1.0, 1.0, 1.0]
mat_diffuse = [0.9, 0.9, 0.9, 1.0]
mat_ambient = [0.3, 0.3, 0.3, 1.0]
no_mat = [0.0, 0.0, 0.0, 1.0]

NUM_TEXTURES = 3
texture_filenames = [
	"textures/floor.bmp",
	"textures/wall.bmp",
	"textures/ceiling.bmp",
]
FLOOR_TEX_IND, WALL_TEX_IND, CEILING_TEX_IND = range(3)


def load_bmp(filename):
	"""quick and dirty bitmap loader...for 24 bit bitmaps with 1 plane only. 
	adapted from: http://nehe.gamedev.net/data/lessons/linux/lesson10.tar.gz
	"""
	file = open(filename, 'rb')
	# seek through the bmp header, up to the width/height:
	file.seek(18, os.SEEK_CUR)

	# read the width
	width_str = file.read(4)
	# I means unsigned int, but that is not necessarily 4 bytes
	# TODO: make this more system agnostic
	w = unpack('I', width_str)[0]

	# read the height 
	height_str = file.read(4)
	h = unpack('I', height_str)[0]

	# calculate the size (assuming 24 bits or 3 bytes per pixel).
	size = w * h * 3

	# read the planes
	planes_str = file.read(2)
	planes = unpack('H', planes_str)[0]

	if planes != 1:
		print 'Planes from %s is not 1: %d' % (filename, planes)
		return False

	# read the bpp
	bpp_str = file.read(2)
	bpp = unpack('H', bpp_str)[0]
	if bpp != 24:
		print 'Bpp from %s is not 24: %d' % (filename, bpp)
		return False

	# seek past the rest of the bitmap header.
	file.seek(24, os.SEEK_CUR)

	# read the data. 
	texel_array = array('B')
	texel_array.fromfile(file, size)
	texels = texel_array.tolist()

	# reverse all of the colors. (bgr -> rgb)
	for i in range(0, size, 3):
		temp = texels[i]
		texels[i] = texels[i+2]
		texels[i+2] = temp

	# we're done.
	return True, texels, w, h


def init_cells():
	cells = []
	for i in range(LENGTH):
		cells.append([NORTH | WEST]*WIDTH)

	# southernmost row
	for i in range(WIDTH):
		cells[LENGTH-1][i] |= SOUTH

	# easternmost column
	for i in range(LENGTH):
		cells[i][WIDTH-1] |= EAST

	return cells


def valid_cell(x, y):
	return x >= 0 and x < WIDTH and y >= 0 and y < LENGTH


def get_xdiff(dir):
	if dir == WEST:
		return -1
	if dir == EAST:
		return 1
	return 0


def get_xdir(diff):
	if diff == -1:
		return WEST
	if diff == 1:
		return EAST
	return 0


def get_ydiff(dir):
	if dir == NORTH:
		return -1
	if dir == SOUTH:
		return 1
	return 0


def get_ydir(diff):
	if diff == -1:
		return NORTH
	if diff == 1:
		return SOUTH
	return 0

def move(startx, starty, dir):
	"""updates startx and starty to new coordinates based on dir
	returns true if the move is valid"""
	
	newx = startx + get_xdiff(dir)
	newy = starty + get_ydiff(dir)

	return valid_cell(newx, newy), newx, newy


dir_str = {NORTH: "north", SOUTH: "south", EAST: "east", WEST: "west"}
opp_dir = {NORTH: SOUTH, SOUTH: NORTH, EAST: WEST, WEST: EAST}


def wall_pos(x, z, wall):
	if (cells[z][x] & wall) == 0 and (wall == SOUTH or wall == EAST):
		valid_cell, newx, newz = move(x, z, wall)
		return opp_dir[wall], newx, newz 
	else:
		return wall, x, z


def knock_down_wall(x, z, dir):
	actual_pos, actual_x, actual_z = wall_pos(x, z, dir)
	cells[actual_z][actual_x] &= ~actual_pos


def generate_maze(x, y):
	"generates the maze"

	checked = 0 # bitfield of checked neighbors
	goal = (x == STARTX and y == STARTY)

	if not valid_cell(x, y):
		return 0

	if (cells[y][x] & VISITED) != 0:
		return 0

	cells[y][x] |= VISITED

	while (checked < ALL_DIRS):
		i = random.randint(0, 3)
		dir = (1 << i)
		checked |= dir
		valid_move, newx, newy = move(x, y, dir)
		if valid_move: # try to move in that direction
			if (cells[newy][newx] & VISITED) == 0: # if not visited
				knock_down_wall(x, y, dir)
				
				# start the generation process at new point
				goal += generate_maze(newx, newy)

	if goal:
		cells[y][x] |= HINT

	return goal


def set_elapsed():
	global elapsed
	elapsed = (glutGet(GLUT_ELAPSED_TIME) - start_time) / 1000

def draw_text(x, y, z, hudmode, center, format, *args):
	font = GLUT_STROKE_MONO_ROMAN
	PADDING = 50.0
	l = 0.0

	buffer_str = format % args
	buffer = ctypes.cast(buffer_str, ctypes.POINTER(constants.GLubyte))
    
	glMatrixMode(GL_MODELVIEW)
	glPushMatrix()
	if hudmode:
		glLoadIdentity()
		glDisable(GL_DEPTH_TEST)
		glMatrixMode(GL_PROJECTION)
		glPushMatrix()
		glLoadIdentity()	
		gluOrtho2D(-1, 1, -1, 1)

	glTranslatef(x, y, z)
	glScalef(1.0/2500.0, 1.0/2500.0, 1.0/2500.0)

	if center:
		l = glutStrokeLength(font, buffer) / 2.0

	first_char_width = glutStrokeWidth(font, buffer[0])
	glTranslatef(-l + PADDING, -first_char_width - PADDING, 0)

	num_chars = len(buffer_str)
	for i in range(num_chars):
		glutStrokeCharacter(font, buffer[i])

	glMatrixMode(GL_MODELVIEW)
	glPopMatrix()

	if hudmode:
		glMatrixMode(GL_PROJECTION)
		glPopMatrix()	
		glEnable(GL_DEPTH_TEST)

def draw_square(texture_name):
	glPushMatrix()
	glTranslatef(0.0, 0.0, -0.5)

	#if do_lighting:
	#	glNormal3f(0.0, 0.0, 1.0)

	modelview = glGetFloatv(GL_MODELVIEW_MATRIX)
	# opengl assumes the matrix is in column-major order,
	# but numpy stores matrices in row-major order [see glMultMatrix(3)]
	# so, transpose it so the matrix multiply (dot) operation below works
	modelview = modelview.transpose()
	for vertex in square_vertices:
		# convert 2D vertex to a 4D homogeneous vertex [see redbook appendix G]
		homogeneous_vertex = vertex + [0, 1]
		generated_vertex = numpy.dot(modelview, homogeneous_vertex).tolist()
		generated_vertex.pop() # remove w coordinate
		print generated_vertex
		wall_vertices.append(generated_vertex)

	glPopMatrix()


def draw_wall(rot):
	glPushMatrix()
	glRotatef(rot, 0.0, 1.0, 0.0)

	#if above:
	#	# draw a line slightly above the wall, to outline the edge
	#	if do_lighting:
	#		glDisable(GL_LIGHTING)
	#	glColor4fv(grid_color)
	#	glLineWidth(0.5)
	#	glBegin(GL_LINES)
	#	glVertex3f(-0.5, 0.501, -0.5)
	#	glVertex3f(0.5, 0.501, -0.5)
	#	glEnd()
	#	if do_lighting:
	#		glEnable(GL_LIGHTING)

	draw_square(texture_names[WALL_TEX_IND])
	glPopMatrix()

def draw_arrowhead():
	if do_lighting:
		glDisable(GL_LIGHTING)
	glColor4f(1.0, 0.0, 0.0, 1.0)
	glBegin(GL_TRIANGLES)
	glVertex3f(0.0, 0.2, 0.0)
	glVertex3f(-0.1, -0.2, 0.0)
	glVertex3f(0.1, -0.2, 0.0)
	glEnd()
	if do_lighting:
		glEnable(GL_LIGHTING)


def draw_floor(overlay_hint):
	glPushMatrix()
	glRotatef(-90.0, 1.0, 0.0, 0.0)

	draw_square(texture_names[FLOOR_TEX_IND])

#	if overlay_hint:
#		if do_lighting:
#			glDisable(GL_LIGHTING)
#		glTranslatef(0.0, 0.0, -0.49)
#		glScalef(0.03, 0.03, 0.03)
#		glColor4f(1.0, 1.0, 1.0, 1.0)
#		glRectf(-1.0, -1.0, 1.0, 1.0)
#		if do_lighting:
#			glEnable(GL_LIGHTING)

	glPopMatrix()


def draw_ceiling():
	glPushMatrix()
	glRotatef(90.0, 1.0, 0.0, 0.0)
	draw_square(texture_names[CEILING_TEX_IND])
	glPopMatrix()


def generate_cell(x, z):
	glPushMatrix()
	glScalef(CELL_SIZE, CELL_SIZE, CELL_SIZE)
	glTranslatef(x, 0.0, z)

	#draw_floor(give_hints and ((cells[z][x] & HINT) != 0))

	#if not above: # only draw the ceiling if bird's eye view is not active
	#	draw_ceiling()

	for i in range(4):
		wall = 1 << i
		if ((cells[z][x]) & wall) != 0:
			draw_wall(-i*90)
	
	#if not above and won and x == GOALX and z == GOALY:
	#	if (do_lighting):
	#		glDisable(GL_LIGHTING)
	#	glColor4f(1.0, 1.0, 1.0, 1.0)
	#	glLineWidth(4.0)
	#	glPushMatrix()
	#	glRotatef(goal_rot, 0.0, 1.0, 0.0)
	#	draw_text(0, 0, 0, False, True, "GOAL!")
	#	glPopMatrix()
	#	if do_lighting:
	#		glEnable(GL_LIGHTING)
	
	glPopMatrix()

def xrotate(angle, vector):
	"rotate angle radians about the x axis"
	# see redbook appendix F
	rot_mat = [ [1, 0, 0, 0],
				[0, cos(angle), -sin(angle), 0],
				[0, sin(angle), cos(angle), 0],
				[0, 0, 0, 1] ]
	return numpy.dot(rot_mat, vector)

	
def yrotate(angle, vector):
	"rotate angle radians about the y axis"
	# see redbook appendix F
	rot_mat = [ [cos(angle), 0, sin(angle), 0],
				[0, 1, 0, 0],
				[-sin(angle), 0, cos(angle), 0],
				[0, 0, 0, 1] ]
	return numpy.dot(rot_mat, vector)

def zrotate(angle, vector):
	"rotate angle radians about the z axis"
	pass

min_x = 9999
max_x = -9999
min_z = 9999
max_z = -9999

def make_wall(x, z, wall_ind):
	"generate vertices for a specific wall"
	global min_x, max_x, min_z, max_z
	vertices = []
	for v in square_vertices:
		# homogenize and convert to a numpy array
		vertex = numpy.array(v + [0, 1])
		#glTranslatef(0, 0, -0.5, 0)
		vertex += [0, 0, -0.5, 0]
		#glRotatef(-wall_ind * 90, 0, 1, 0)
		angle = radians(-wall_ind*90)
		vertex = yrotate(angle, vertex)
		#glTranslatef(x, 0, z)
		vertex += [x, 0, z, 0]
		#glScalef(CELL_SIZE, CELL_SIZE, CELL_SIZE)
		vertex *= CELL_SIZE
		vertex = vertex[0:-1] # remove w coordinate
		min_x = min(min_x, vertex[0])
		max_x = max(max_x, vertex[0])
		min_z = min(min_z, vertex[2])
		max_z = max(max_z, vertex[2])
		vertices.append(vertex.tolist())
	return vertices

def make_walls():
	"generate vertices for all walls"
	global wall_vertices

	for i in range(WIDTH):
		for j in range(LENGTH):
			for k in range(4): # for each wall (n, e, s, w)
				wall = 1 << k
				if ((cells[j][i]) & wall) != 0: # if the cell has a wall there
					wall_vertices += make_wall(i, j, k)
			#generate_cell(i, j)

def make_floor():
	"generate vertices for the floor"

	global floor_vertices

	half = CELL_SIZE/2
	y = -half
	x_min = -half
	z_min = -half
	z_max = (CELL_SIZE * WIDTH) - half
	x_max = (CELL_SIZE * LENGTH) - half
	floor_vertices = [	[x_min, y, z_min],
						[x_max, y, z_min],
						[x_max, y, z_max],
						[x_min, y, z_max]  ]
def draw_walls():
	glBindTexture(GL_TEXTURE_2D, texture_names[WALL_TEX_IND])
	glTexCoordPointerf(wall_tex_coords * (len(wall_vertices)/4))
	glVertexPointerf(wall_vertices)
	glDrawArrays(GL_QUADS, 0, len(wall_vertices))

def draw_floor():
	glBindTexture(GL_TEXTURE_2D, texture_names[FLOOR_TEX_IND])
	glTexCoordPointerf(floor_tex_coords * (len(wall_vertices)/4))
	glVertexPointerf(floor_vertices)
	glDrawArrays(GL_QUADS, 0, len(floor_vertices))


def draw_cells():
	draw_walls()
	draw_floor()


def draw_hud():
	if do_lighting:
		glDisable(GL_LIGHTING)

	if won:
		if above:
			glColor4f(1.0, 1.0, 0.0, 1.0)
		else:
			glColor4f(1.0, 1.0, 1.0, 1.0)
		glLineWidth(1.5)
		draw_text(0, 0, 0, True, True, \
			"Congratulations! You have won the game.")

	if show_elapsed:
		glColor4f(1.0, 1.0, 1.0, 1.0)
		draw_text(-1, 1, 0, True, False, "elapsed time: %d", elapsed)

	if do_lighting:
		glEnable(GL_LIGHTING)


def display():
	global xrot, yrot

	centerx = -(WIDTH - 1.0) * CELL_SIZE * 0.5
	centerz = -(LENGTH - 1.0) * CELL_SIZE * 0.5

	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
	glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()

	if above:
		gluLookAt(0.0, birds_eye_height, 0.0, # eye
			0.0, 0.0, 0.0, # at
			0.0, 0.0, -1.0) # up

		# center the maze
		glTranslatef(centerx, 0.0, centerz)

		glPushMatrix()
		glTranslatef(-player_xpos, 0.0, -player_zpos)
		glRotatef(yrot, 0.0, 1.0, 0.0)
		glScalef(CELL_SIZE, CELL_SIZE, CELL_SIZE)
		glRotatef(-90.0, 1.0, 0.0, 0.0)
		draw_arrowhead()
		glPopMatrix()
	else:
		if xrot > 90.0:
			xrot = 90.0
		if xrot < -90.0:
			xrot = -90.0
		glRotatef(xrot, 1.0, 0.0, 0.0)
		glRotatef(-yrot, 0.0, 1.0, 0.0)
		glTranslatef(player_xpos, 0.0, player_zpos)

	if do_lighting:
		glPushMatrix()
		glTranslatef(-player_xpos, 0.0, -player_zpos)
		glLightfv(GL_LIGHT0, GL_POSITION, light_position)
		glDisable(GL_LIGHTING)
		glTranslatef(light_position[0], light_position[1], light_position[2])
		glColor4f(1.0, 1.0, 1.0, 1.0)
		glutSolidSphere(CELL_SIZE/20.0, 45, 45)
		glEnable(GL_LIGHTING)
		glPopMatrix()

	draw_cells()
	draw_hud() # this must be called last, so the text is on top

	glFlush()
	glutSwapBuffers()


def wall_exists(old_x, old_y, x, y):
	xdiff = x - old_x
	ydiff = y - old_y

	if xdiff != 0:
		dir = get_xdir(xdiff)
	else:
		dir = get_ydir(ydiff)
	
	actual_pos, actual_old_x, actual_old_y = wall_pos(old_x, old_y, dir)
	
	return cells[actual_old_y][actual_old_x] & actual_pos

def player_pos_to_cell_pos(player_x, player_y):
	cell_x = int(floor((-player_x + (CELL_SIZE/2.0))/CELL_SIZE))
	cell_y = int(floor((-player_y + (CELL_SIZE/2.0))/CELL_SIZE))
	return cell_x, cell_y


old_cell_x = -1
old_cell_y = -1
old_playerx = -1
old_playerz = -1

def collision_check():
	"""sets player_xpos and player_zpos back to old values if there was a
	collision returns True if there was a collision, False otherwise
	"""

	global old_cell_x, old_cell_y, old_playerx, old_playerz, \
		player_xpos, player_zpos

	ret = False

	cell_x, cell_y = player_pos_to_cell_pos(player_xpos, player_zpos)

	if old_cell_x != -1 and old_cell_y != -1 \
			and old_playerx != -1 and old_playerz != -1 \
			and (old_cell_x != cell_x or old_cell_y != cell_y) \
			and (wall_exists(old_cell_x, old_cell_y, cell_x, cell_y)):
		player_xpos = old_playerx
		player_zpos = old_playerz
		cell_x = old_cell_x
		cell_y = old_cell_y
		ret = True
	
	old_playerx = player_xpos
	old_playerz = player_zpos
	old_cell_x = cell_x
	old_cell_y = cell_y

	return ret


def timer(value):
	global goal_rot
	
	# rotate the "GOAL!" sign
	goal_rot -= goal_rot_delta
	if goal_rot < 0.0:
		goal_rot += 360.0

	if not won:
		set_elapsed()

	glutPostRedisplay()
	glutTimerFunc(timer_repeat, timer, 0)


def check_won():
	global won, timer_repeat, timer_enabled

	cell_x, cell_y = player_pos_to_cell_pos(player_xpos, player_zpos)

	won = (cell_x == GOALX and cell_y == GOALY)
	if won:
		set_elapsed()
		show_elapsed = True
		goal_rot = yrot
		timer_repeat /= 10
		if not timer_enabled:
			timer_enabled = True
			glutTimerFunc(timer_repeat, timer, 0)
		
		print "congratulations! you won!"


def ztrans(dir):
	"move forwards (dir = 1) or backwards (dir = -1)"
	global player_xpos, player_zpos
	if not won:
		check_won()
	player_xpos += dir * ztrans_delta * sin(yrot * rad_per_deg)
	player_zpos += dir * ztrans_delta * cos(yrot * rad_per_deg)
	if collision_checking:
		collision_check()


def xtrans(dir):
	global player_xpos, player_zpos
	if not won:
		check_won()
	player_xpos += dir * xtrans_delta * cos(yrot * rad_per_deg)
	player_zpos -= dir * xtrans_delta * sin(yrot * rad_per_deg)
	if collision_checking:
		collision_check()

def reshape(w, h):
   glViewport(0, 0, w, h)
   glMatrixMode(GL_PROJECTION)
   glLoadIdentity()
   gluPerspective(FOV, w/h, 1.0, zfar_pers)
   glMatrixMode(GL_MODELVIEW)
   glLoadIdentity()

def toggle_above():
	global above, widest, birds_eye_height, zfar_pers
	above = not above

	widest = max(WIDTH, LENGTH) * CELL_SIZE
	birds_eye_height = (widest / 2.0) / tan(FOV / 2.0)
	birds_eye_height *= 1.5
	zfar_pers = birds_eye_height * 1.5

	viewport = glGetIntegerv(GL_VIEWPORT)
	reshape(viewport[2], viewport[3])

def set_grab_state():
	if grab_mouse:
		glutSetCursor(GLUT_CURSOR_NONE)
	else:
		glutSetCursor(GLUT_CURSOR_LEFT_ARROW)


def key_pressed(key, x, y):
	global collision_checking, do_texturing, do_lighting, give_hints, \
		grab_mouse, show_elapsed, timer_enabled
	if key == 'w': # move forwards
		ztrans(1)
	elif key == 'a': # strafe left
		xtrans(1)
	elif key == 's': # move backwards
		ztrans(-1)
	elif key == 'd': # strafe right
		xtrans(-1)
	elif key == 'b': # toggle bird's eye view
		toggle_above()
	elif key == 'c': # toggle collision checking
		collision_checking = not collision_checking
	elif key == 't': # toggle texturing
		do_texturing = not do_texturing
		if do_texturing:
			glEnableClientState(GL_TEXTURE_COORD_ARRAY)
		else:
			glDisableClientState(GL_TEXTURE_COORD_ARRAY)
	elif key == 'l': # toggle lighting
		do_lighting = not do_lighting
		if do_lighting:
			glEnable(GL_LIGHTING)
		else:
			glDisable(GL_LIGHTING)
	elif key == 'h': # toggle bread crumb trail
		give_hints = not give_hints
	elif key == 'm': # toggle mouse grabbing
		grab_mouse = not grab_mouse
		set_grab_state()
	elif key == 'e': # toggle display of elapsed time
		show_elapsed = not show_elapsed
		if show_elapsed and not timer_enabled:
			set_elapsed()
			timer_enabled = True
			glutTimerFunc(timer_repeat, timer, 0)
	elif ord(key) == 27: # ESC exits
		sys.exit(0)

	glutPostRedisplay()


def special_key_pressed(key, x, y):
	global xrot, yrot, birds_eye_height
	yrd = yrot_delta

	if above:
		yrd *= 3.0

	if key == GLUT_KEY_LEFT: # turn to the left
		yrot += yrd
	elif key == GLUT_KEY_RIGHT: # turn to the right
		yrot -= yrd
	elif key == GLUT_KEY_UP:
		if above: # decrease height above maze
			birds_eye_height -= 1
		else: # look up
			xrot -= xrot_delta
	elif key == GLUT_KEY_DOWN:
		if above: # increase height above maze
			birds_eye_height += 1
		else: # look down
			xrot += xrot_delta

	glutPostRedisplay()


def mouse(button, state, x, y):
	global grab_mouse
	if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
		grab_mouse = True
		set_grab_state()


def motion(x, y):
	global xrot, yrot

	if (grab_mouse and x != CENTERX and y != CENTERY):
		glutWarpPointer(int(CENTERX), int(CENTERY))
		
		if (not above):
			xrot -= (CENTERY - y) * MOUSE_SENSITIVITY

		yrot += (CENTERX - x) * MOUSE_SENSITIVITY

		glutPostRedisplay()


def init_lighting():
	if not do_lighting:
		glDisable(GL_LIGHTING)
	else:
		glEnable(GL_LIGHTING)
		glEnable(GL_LIGHT0)

		glLightfv(GL_LIGHT0, GL_POSITION, light_position)
		glLightfv(GL_LIGHT0, GL_DIFFUSE, light_diffuse)
		glLightfv(GL_LIGHT0, GL_AMBIENT, light_ambient)

		glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_TRUE)

		glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, mat_diffuse)
		glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, mat_ambient)
		glLightModelfv(GL_LIGHT_MODEL_AMBIENT, global_ambient)


def bind_texture(name, texels, w,  h):
	glBindTexture(GL_TEXTURE_2D, name)
	glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_BLEND)
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, \
		GL_RGB, GL_UNSIGNED_BYTE, texels)


def init_textures():
	global texture_names
	texture_names = glGenTextures(NUM_TEXTURES)

	for i in range(NUM_TEXTURES):
		# TODO: replace load_bmp with PIL functions (see NeHe lesson 18)
		succeeded, texels, w, h = load_bmp(texture_filenames[i])
		if succeeded:
			bind_texture(int(texture_names[i]), texels, w, h)
		else:
			print "unable to open %s" % texture_filenames[i]
	
	glEnable(GL_TEXTURE_2D)
	glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)


def init_arrays():
	glEnableClientState(GL_VERTEX_ARRAY)
	#glEnableClientState(GL_TEXTURE_COORD_ARRAY)
	#glVertexPointer(4, GL_FLOAT, 0, square_vertices)
	#glVertexPointerf(square_vertices)
	#glTexCoordPointer(2, GL_FLOAT, 0, tex_coords)


def init():
	global ztrans_delta, xtrans_delta, player_xpos, player_zpos, cells, \
		start_time

	random.seed(123456)
    
	glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()

	glEnable(GL_DEPTH_TEST)
	glEnable(GL_NORMALIZE)
	glShadeModel(GL_SMOOTH)

	# (0.561, 0.761, 0.929) is a sky blue
	glClearColor(0.561, 0.761, 0.929, 1.0)
	glColor4f(1.0, 1.0, 0.0, 1.0)

	if do_lighting:
		init_lighting()

	ztrans_delta = CELL_SIZE / 15.0
	xtrans_delta = ztrans_delta / 3.0
	
	player_xpos = -GOALX * CELL_SIZE
	player_zpos = -GOALY * CELL_SIZE
	player_xpos = -STARTX * CELL_SIZE
	player_zpos = -STARTY * CELL_SIZE
	collision_check()

	cells = init_cells()
	generate_maze(GOALX, GOALY)

	cells[GOALY][GOALX] &= ~NORTH

	start_time = glutGet(GLUT_ELAPSED_TIME)
	key_pressed('e', 0, 0) # enable display of elapsed time
	key_pressed('m', 0, 0) # enable mouse grabbing 
	key_pressed('t', 0, 0) # enable texturing
	
	init_textures()

	glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()
	make_walls()
	make_floor()

	init_arrays()


if __name__ == '__main__':
	glutInit(sys.argv)
	glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
	glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
	glutInitWindowPosition(0, 0)
	glutCreateWindow("aMAZEing")
	glutDisplayFunc(display)
	glutReshapeFunc(reshape)
	glutKeyboardFunc(key_pressed)
	glutSpecialFunc(special_key_pressed)
	glutMouseFunc(mouse)
	glutPassiveMotionFunc(motion)
	if sys.platform == "darwin":
		import objc
		bndl = objc.loadBundle('CoreGraphics', globals(), 
			'/System/Library/Frameworks/ApplicationServices.framework') 
		objc.loadBundleFunctions(bndl, globals(), [ 
			('CGSetLocalEventsSuppressionInterval',
				''.join((objc._C_INT, objc._C_FLT))), 
		]) 
		CGSetLocalEventsSuppressionInterval(0)
	init()
	glutMainLoop()

