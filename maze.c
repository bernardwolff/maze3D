#include <glut.h>
#include <stdlib.h>
#include <math.h>
#include <limits.h>
#include <stdio.h>
#include <time.h>
#include <string.h>
#include <stdarg.h>

#define WINDOW_WIDTH 800
#define WINDOW_HEIGHT 600

// mouse sensitivity, higher number means greater sensitivity
#define MOUSE_SENSITIVITY 0.2

#define FOV 45
float zfar_pers = 500.0;

// the maze is WIDTH x LENGTH cells
#define WIDTH 25
#define LENGTH 25

// cells are cubes with this width
#define CELL_SIZE 10.0

int cells[WIDTH][LENGTH];

// the goal cell
#define GOALX (WIDTH-1)
#define GOALY 0

// the cell that the player starts out in
#define STARTX 0
#define STARTY (LENGTH-1)

// wall constants
#define NORTH 1
#define EAST 2
#define SOUTH 4
#define WEST 8

#define ALL_DIRS (NORTH | SOUTH | EAST | WEST)

#define VISITED 16
#define HINT 32

// whether to use textures
int do_texturing = 1;

// whether to do lighting
int do_lighting = 1;

// whether the camera is above the maze
int above = 0;

// whether to perform collision checking
int collision_checking = 1;

// how high above the maze the camera is
float birds_eye_height = 0.0;

// whether the player has won the game
int won = 0;

int give_hints = 0;

float yrot = 0.0;
float yrot_delta = 5.0;

float xrot = 0.0;
float xrot_delta = 5.0;

float player_xpos = 0.0; //-85.714348;
float player_zpos = 0.0; //-87.5;

float ztrans_delta = 0.0;
float xtrans_delta = 0.0;

float goal_rot = 0.0;
float goal_rot_delta = 2.5;

unsigned int timer_repeat = 250;

float rad_per_deg = M_PI/180.0;

int dont_grab_mouse = 0;

// game start time in ms
int start_time = 0;

// whether to show elapsed time
int show_elapsed = 0;

int elapsed = 0;

// whether to show remaining time
int show_remaining = 0;

int timer_enabled = 0;

#define x1 -0.5
#define y1 -0.5
#define x2 0.5
#define y2 0.5
GLfloat square_vertices[][2] = {{x1, y1}, {x2, y1}, {x2, y2}, {x1, y2}};
GLfloat tex_coords[][2] = {{0.0, 0.0}, {1.0, 0.0}, {1.0, 1.0}, {0.0, 1.0}};
GLubyte indices[] = {0, 1, 2, 3};

GLfloat grid_color[] = {1.0, 1.0, 1.0, 1.0};

GLfloat light_position[] = {0.0, 0.0, 0.0, 1.0};
GLfloat global_ambient[] = {0.8, 0.8, 0.8, 1.0};
GLfloat light_diffuse[] = { 1.0, 1.0, 1.0, 1.0 };
GLfloat light_ambient[] = { 1.0, 1.0, 1.0, 1.0 };
GLfloat mat_diffuse[] = {0.9, 0.9, 0.9, 1.0};
GLfloat mat_ambient[] = {0.3, 0.3, 0.3, 1.0};
GLfloat no_mat[] = { 0.0, 0.0, 0.0, 1.0 };

#define NUM_TEXTURES 3
const char *texture_filenames[] = {
	"textures/floor.bmp",
	"textures/wall.bmp",
	"textures/ceiling.bmp"
};
GLuint texture_names[NUM_TEXTURES];
enum texture_indices { FLOOR_TEX_IND, WALL_TEX_IND, CEILING_TEX_IND };


// quick and dirty bitmap loader...for 24 bit bitmaps with 1 plane only. 
// adapted from: http://nehe.gamedev.net/data/lessons/linux/lesson10.tar.gz
int load_bmp(const char *filename, GLubyte **texels,
	unsigned long *w, unsigned long *h)
{
    FILE *file;
    unsigned long size;       // size of the image in bytes.
    unsigned long i;          // standard counter.
    unsigned short int planes;// number of planes in image (must be 1) 
    unsigned short int bpp;   // number of bits per pixel (must be 24)
    char temp;                // temporary color storage for bgr-rgb conversion.

    // make sure the file is there.
    if ((file = fopen(filename, "rb")) == NULL) {
		printf("File Not Found : %s\n",filename);
		return 0;
    }
    
    // seek through the bmp header, up to the width/height:
    fseek(file, 18, SEEK_CUR);

    // read the width
    if ((i = fread(w, 4, 1, file)) != 1) {
		printf("Error reading width from %s.\n", filename);
		return 0;
    }
    //printf("Width of %s: %lu\n", filename, *w);
    
    // read the height 
    if ((i = fread(h, 4, 1, file)) != 1) {
		printf("Error reading height from %s.\n", filename);
		return 0;
    }
    //printf("Height of %s: %lu\n", filename, *h);
    
    // calculate the size (assuming 24 bits or 3 bytes per pixel).
    size = (*w) * (*h) * 3;

    // read the planes
    if ((fread(&planes, 2, 1, file)) != 1) {
		printf("Error reading planes from %s.\n", filename);
		return 0;
    }
    if (planes != 1) {
		printf("Planes from %s is not 1: %u\n", filename, planes);
		return 0;
    }

    // read the bpp
    if ((i = fread(&bpp, 2, 1, file)) != 1) {
		printf("Error reading bpp from %s.\n", filename);
		return 0;
    }
    if (bpp != 24) {
		printf("Bpp from %s is not 24: %u\n", filename, bpp);
		return 0;
    }
	
    // seek past the rest of the bitmap header.
    fseek(file, 24, SEEK_CUR);

    // read the data. 
    *texels = (GLubyte *)malloc(size);
	
    if (*texels == NULL) {
		printf("Error allocating memory for color-corrected image data\n");
		return 0;	
    }

    if ((i = fread(*texels, size, 1, file)) != 1) {
		printf("Error reading image data from %s.\n", filename);
		return 0;
    }

    for (i = 0; i < size; i += 3) { // reverse all of the colors. (bgr -> rgb)
		temp = (*texels)[i];
		(*texels)[i] = (*texels)[i+2];
		(*texels)[i+2] = temp;
    }
    
    // we're done.
    return 1;
}

// returns a random integer in the range [M, N]
int rand_int(int M, int N)
{
	return M + rand() / (RAND_MAX / (N - M + 1) + 1);
}

int max(int a, int b)
{
	return a > b ? a : b;
}

int min(int a, int b)
{
	return a < b ? a : b;
}

void init_cells()
{
	int i, j;

	for (i = 0; i < WIDTH; i++)
		for (j = 0; j < LENGTH; j++)
			cells[i][j] = NORTH | WEST;

	// southernmost row
	for (i = 0; i < WIDTH; i++)
		cells[i][LENGTH-1] |= SOUTH;

	// easternmost column
	for (j = 0; j < LENGTH; j++)
		cells[WIDTH-1][j] |= EAST;
}

int valid_cell(int x, int y)
{
	return x >= 0 && x < WIDTH && y >= 0 && y < LENGTH;
}

int get_xdiff(int dir)
{
	if (dir == WEST)
		return -1;
	if (dir == EAST)
		return 1;
	return 0;
}

int get_xdir(int diff)
{
	if (diff == -1)
		return WEST;
	if (diff == 1)
		return EAST;
	return 0;
}

int get_ydiff(int dir)
{
	if (dir == NORTH)
		return -1;
	if (dir == SOUTH)
		return 1;
	return 0;
}

int get_ydir(int diff)
{
	if (diff == -1)
		return NORTH;
	if (diff == 1)
		return SOUTH;
	return 0;
}

// updates startx and starty to new coordinates based on dir
// returns true if the move is valid
int move(int *startx, int *starty, int dir)
{
	int newx = *startx;
	int newy = *starty;

	newx += get_xdiff(dir);
	newy += get_ydiff(dir);

	*startx = newx;
	*starty = newy;
	
	return valid_cell(newx, newy);
}

const char *dir_str(int dir)
{
	switch (dir) {
		case NORTH:
			return "north";
		case SOUTH:
			return "south";
		case EAST:
			return "east";
		case WEST:
			return "west";
	}
	return "bad direction";
}

int opp_dir(int dir)
{
	switch(dir) {
		case NORTH:
			return SOUTH;
		case SOUTH:
			return NORTH;
		case EAST:
			return WEST;
		case WEST:
			return EAST;
	}
	return 0;
}

int wall_pos(int *x, int *z, int wall)
{
	if (!(cells[*x][*z] & wall)
			&& (wall == SOUTH || wall == EAST)) {
		move(x, z, wall);
		return opp_dir(wall);
	}

	return wall;
}

void knock_down_wall(int x, int z, int dir)
{
	int actual_pos = wall_pos(&x, &z, dir);
	cells[x][z] &= ~actual_pos;
}	

// generate the maze
int generate(int x, int y)
{
	int i = 0, dir, newx, newy;
	int checked = 0; // bitfield of checked neighbors
	int goal = x == STARTX && y == STARTY;

	if (!valid_cell(x, y))
		return 0;

	if (cells[x][y] & VISITED)
		return 0;

	cells[x][y] |= VISITED;

	while (checked < ALL_DIRS) {
		i = rand_int(0, 3);
		dir = (1 << i);
		checked |= dir;
		newx = x;
		newy = y;
		if (move(&newx, &newy, dir)) { // try to move in that direction
			if (!(cells[newx][newy] & VISITED)) { // if not visited
				knock_down_wall(x, y, dir);
				
				// start the generation process at new point
				goal += generate(newx, newy);
			}
		}
	}

	if (goal)
		cells[x][y] |= HINT;

	return goal;
}

void set_elapsed()
{
	elapsed = (glutGet(GLUT_ELAPSED_TIME) - start_time) / 1000;
}

void draw_text(GLfloat x, GLfloat y, GLfloat z, int hudmode, int center,
	char *format, ...)
{
	va_list args;
	char buffer[200];
	int i;
	float l = 0;
	static void *font = GLUT_STROKE_MONO_ROMAN;
	static const int PADDING = 50;

	va_start(args, format);
	vsprintf(buffer, format, args);
	va_end(args);
    
	glMatrixMode(GL_MODELVIEW);	
	glPushMatrix();				
	if (hudmode) {
		glLoadIdentity();

		glDisable(GL_DEPTH_TEST);
		glMatrixMode(GL_PROJECTION);
		glPushMatrix();				
		glLoadIdentity();			
		gluOrtho2D(-1, 1, -1, 1);	
	}

	glTranslatef(x, y, z);
	glScalef(1.0/2500.0, 1.0/2500.0, 1.0/2500.0);

	if (center) {
		l = glutStrokeLength(font, buffer) / 2.0;
	}

	glTranslatef(-l + PADDING, -glutStrokeWidth(font, buffer[0]) - PADDING, 0);

    for (i = 0; buffer[i] != '\0'; i++) {
		glutStrokeCharacter(font, buffer[i]);
	}

	glMatrixMode(GL_MODELVIEW); 
	glPopMatrix();
	if (hudmode) {
		glMatrixMode(GL_PROJECTION);
		glPopMatrix();				  
		glEnable(GL_DEPTH_TEST);
	}		
}

void draw_square(int texture_name)
{
	if (do_texturing && texture_name) {
		glEnable(GL_TEXTURE_2D);
		glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE);
		glBindTexture(GL_TEXTURE_2D, texture_name);
	}

	glPushMatrix();
	glTranslatef(0.0, 0.0, -0.5);

	if (do_lighting) glNormal3f(0.0, 0.0, 1.0);

	glDrawElements(GL_POLYGON, 4, GL_UNSIGNED_BYTE, indices);

	/*glBegin(GL_POLYGON);
	if (do_texturing) glTexCoord2f(0.0, 0.0);
	glVertex2f(x1, y1);
	if (do_texturing) glTexCoord2f(1.0, 0.0);
	glVertex2f(x2, y1);
	if (do_texturing) glTexCoord2f(1.0, 1.0);
	glVertex2f(x2, y2);
	if (do_texturing) glTexCoord2f(0.0, 1.0);
	glVertex2f(x1, y2);
	glEnd();*/

//	glRectf(x1, y1, x2, y2);

	glPopMatrix();

	if (do_texturing) glDisable(GL_TEXTURE_2D);
}

void draw_wall(int rot)
{
	glPushMatrix();
	glRotatef(rot, 0.0, 1.0, 0.0);

	if (above) {
		// draw a line slightly above the wall, to outline the edge
		if (do_lighting) glDisable(GL_LIGHTING);
		glColor4fv(grid_color);
		glLineWidth(0.5);
		glBegin(GL_LINES);
		glVertex3f(-0.5, 0.501, -0.5);
		glVertex3f(0.5, 0.501, -0.5);
		glEnd();
		if (do_lighting) glEnable(GL_LIGHTING);
	}

	draw_square(texture_names[WALL_TEX_IND]);
	glPopMatrix();
}

void draw_arrowhead()
{
	if (do_lighting) glDisable(GL_LIGHTING);
	glColor4f(1.0, 0.0, 0.0, 1.0);
	glBegin(GL_TRIANGLES);
	glVertex3f(0.0, 0.2, 0.0);
	glVertex3f(-0.1, -0.2, 0.0);
	glVertex3f(0.1, -0.2, 0.0);
	glEnd();
	if (do_lighting) glEnable(GL_LIGHTING);
}

void draw_floor(int overlay_hint)
{
	glPushMatrix();
	glRotatef(-90.0, 1.0, 0.0, 0.0);

	draw_square(texture_names[FLOOR_TEX_IND]);

	if (overlay_hint) {
		if (do_lighting) glDisable(GL_LIGHTING);
		glTranslatef(0.0, 0.0, -0.49);
		glScalef(0.03, 0.03, 0.03);
		glColor4f(1.0, 1.0, 1.0, 1.0);
		glRectf(-1.0, -1.0, 1.0, 1.0);
		if (do_lighting) glEnable(GL_LIGHTING);
	}

	glPopMatrix();
}

void draw_ceiling()
{
	glPushMatrix();
	glRotatef(90.0, 1.0, 0.0, 0.0);
	draw_square(texture_names[CEILING_TEX_IND]);
	glPopMatrix();
}

void draw_cell(int x, int z)
{
	int i, wall;

	glPushMatrix();
	glScalef(CELL_SIZE, CELL_SIZE, CELL_SIZE);
	glTranslatef(x, 0.0, z);

	draw_floor(give_hints && (cells[x][z] & HINT));

	if (!above) // only draw the ceiling if bird's eye view is not active
		draw_ceiling();

	for (i = 0; i < 4; i++) {
		wall = 1 << i;
		if (cells[x][z] & wall)
			draw_wall(-i*90);
	}
	
	if (!above && won && x == GOALX && z == GOALY) {
		if (do_lighting) glDisable(GL_LIGHTING);
		glColor4f(1.0, 1.0, 1.0, 1.0);
		glLineWidth(4.0);
		glPushMatrix();
		glRotatef(goal_rot, 0.0, 1.0, 0.0);
		draw_text(0, 0, 0, 0, 1, "GOAL!");
		glPopMatrix();
		if (do_lighting) glEnable(GL_LIGHTING);
	}
	
	glPopMatrix();
}

void draw_cells()
{
	int i, j;

	for (i = 0; i < WIDTH; i++) {
		for (j = 0; j < LENGTH; j++) {
			draw_cell(i, j);
		}
	}
}

void draw_hud()
{
	if (do_lighting) glDisable(GL_LIGHTING);

	if (won) {
		if (above)
			glColor4f(1.0, 1.0, 0.0, 1.0);
		else
			glColor4f(1.0, 1.0, 1.0, 1.0);
		glLineWidth(1.5);
		draw_text(0, 0, 0, 1, 1, "Congratulations! You have won the game.");
	}

	if (show_elapsed) {
		glColor4f(1.0, 1.0, 1.0, 1.0);
		draw_text(-1, 1, 0, 1, 0, "elapsed time: %d", elapsed);
	}

	if (do_lighting) glEnable(GL_LIGHTING);
}

void display(void)
{
	int centerx;
	int centerz;

	centerx = -(WIDTH - 1.0) * CELL_SIZE * 0.5;
	centerz = -(LENGTH - 1.0) * CELL_SIZE * 0.5;

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    glMatrixMode(GL_MODELVIEW);
	glLoadIdentity();

	if (above) {
		gluLookAt(0.0, birds_eye_height, 0.0, // eye
			0.0, 0.0, 0.0, // at
			0.0, 0.0, -1.0); // up

		// center the maze
		glTranslatef(centerx, 0.0, centerz);

		glPushMatrix();
		glTranslatef(-player_xpos, 0.0, -player_zpos);
		glRotatef(yrot, 0.0, 1.0, 0.0);
		glScalef(CELL_SIZE, CELL_SIZE, CELL_SIZE);
		glRotatef(-90.0, 1.0, 0.0, 0.0);
		draw_arrowhead();
		glPopMatrix();
	} else {
		if (xrot > 90.0)
			xrot = 90.0;
		if (xrot < -90.0)
			xrot = -90.0;
		glRotatef(xrot, 1.0, 0.0, 0.0);
		glRotatef(-yrot, 0.0, 1.0, 0.0);
		glTranslatef(player_xpos, 0.0, player_zpos);
	}

	if (do_lighting) {
		glPushMatrix();
		glTranslatef(-player_xpos, 0.0, -player_zpos);
		glLightfv(GL_LIGHT0, GL_POSITION, light_position);
		glDisable(GL_LIGHTING);
		glTranslatef(light_position[0], light_position[1], light_position[2]);
		glColor4f(1.0, 1.0, 1.0, 1.0);
		glutSolidSphere(CELL_SIZE/20.0, 45, 45);
		glEnable(GL_LIGHTING);
		glPopMatrix();
	}

	draw_cells();
	draw_hud(); // this must be called last, so the text is on top

	glFlush();
    glutSwapBuffers();
}

int wall_exists(int old_x, int old_y, int x, int y)
{
	int xdiff = x - old_x;
	int ydiff = y - old_y;
	int dir;

	if (xdiff != 0)
		dir = get_xdir(xdiff);
	else
		dir = get_ydir(ydiff);
	
	int actual_pos = wall_pos(&old_x, &old_y, dir);
	
	return cells[old_x][old_y] & actual_pos;
}

void player_pos_to_cell_pos(float player_x, float player_y,
							int *cell_x, int *cell_y)
{
	*cell_x = floor((-player_x + (CELL_SIZE/2.0))/CELL_SIZE);
	*cell_y = floor((-player_y + (CELL_SIZE/2.0))/CELL_SIZE);
}

// sets player_xpos and player_zpos back to old values if there was a collision
// returns 1 if there was a collision, 0 otherwise
int collision_check()
{
	static int old_cell_x = -1;
	static int old_cell_y = -1;
	static float old_playerx = -1;
	static float old_playerz = -1;

	int cell_x, cell_y, ret = 0;

	player_pos_to_cell_pos(player_xpos, player_zpos, &cell_x, &cell_y);

	if (old_cell_x != -1 && old_cell_y != -1
			&& old_playerx != -1 && old_playerz != -1
			&& (old_cell_x != cell_x || old_cell_y != cell_y)
			&& (wall_exists(old_cell_x, old_cell_y, cell_x, cell_y))) {
		player_xpos = old_playerx;
		player_zpos = old_playerz;
		cell_x = old_cell_x;
		cell_y = old_cell_y;

		ret = 1;
	}
	
	old_playerx = player_xpos;
	old_playerz = player_zpos;
	old_cell_x = cell_x;
	old_cell_y = cell_y;

	return ret;
}

void timer(int value)
{
	// rotate the "GOAL!" sign
	goal_rot -= goal_rot_delta;
	if (goal_rot < 0.0)
		goal_rot += 360.0;

	if (!won)	
		set_elapsed();

	glutPostRedisplay();
	glutTimerFunc(timer_repeat, timer, 0);
}

void check_won()
{
	int cell_x, cell_y;
	
	player_pos_to_cell_pos(player_xpos, player_zpos, &cell_x, &cell_y);

	won = cell_x == GOALX && cell_y == GOALY;
	if (won) {
		set_elapsed();
		show_elapsed = 1;
		goal_rot = yrot;
		timer_repeat /= 10;
		if (!timer_enabled) {
			timer_enabled = 1;
			glutTimerFunc(timer_repeat, timer, 0);
		}
		printf("congratulations! you won!\n");
	
	}
}

// move forwards (dir = 1) or backwards (dir = -1)
void ztrans(int dir)
{
	if (!won) check_won();
	player_xpos += dir * ztrans_delta * sin(yrot * rad_per_deg);
	player_zpos += dir * ztrans_delta * cos(yrot * rad_per_deg);
	if (collision_checking) collision_check();
}

void xtrans(int dir)
{
	if (!won) check_won();
	player_xpos += dir * xtrans_delta * cos(yrot * rad_per_deg);
	player_zpos -= dir * xtrans_delta * sin(yrot * rad_per_deg);
	if (collision_checking) collision_check();
}

void reshape(int w, int h)
{
   glViewport(0, 0, (GLsizei)w, (GLsizei)h);
   glMatrixMode(GL_PROJECTION);
   glLoadIdentity();
   gluPerspective(FOV, (GLfloat)w/(GLfloat)h, 1.0, zfar_pers);
   glMatrixMode(GL_MODELVIEW);
   glLoadIdentity();
}

void toggle_above()
{
	float widest;
	GLint viewport[4];

	above = !above;

	widest = max(WIDTH, LENGTH) * CELL_SIZE;
	birds_eye_height = ((float)widest/2.0) / tan((float)FOV/2.0);
	birds_eye_height *= 1.5;
	zfar_pers = birds_eye_height * 1.5;

	glGetIntegerv(GL_VIEWPORT,viewport);
	reshape(viewport[2], viewport[3]);
}

void key_pressed(unsigned char key, int x, int y)
{
	switch (key) {
		case 'w': // move forwards
			ztrans(1);
			break;
		case 'a': // strafe left
			xtrans(1);
			break;
		case 's': // move backwards
			ztrans(-1);
			break;
		case 'd': // strafe right
			xtrans(-1);
			break;
		case 'b': // toggle bird's eye view
			toggle_above();
			break;
		case 'c': // toggle collision checking
			collision_checking = !collision_checking;
			break;
		case 't': // toggle texturing
			do_texturing = !do_texturing;
			break;
		case 'l': // toggle lighting
			do_lighting = !do_lighting;
			if (do_lighting) glEnable(GL_LIGHTING);
			else glDisable(GL_LIGHTING);
			break;
		case 'h': // toggle bread crumb trail
			give_hints = !give_hints;
			break;
		case 'm': // toggle mouse grabbing
			dont_grab_mouse = !dont_grab_mouse;
			break;
		case 'e': // toggle display of elapsed time
			show_elapsed = !show_elapsed;
			if (show_elapsed && !timer_enabled) {
				set_elapsed();
				timer_enabled = 1;
				glutTimerFunc(timer_repeat, timer, 0);
			}
			break;
		case 27: // ESC exits
			exit(0);
	}

	glutPostRedisplay();
}

void special_key_pressed(int key, int x, int y)
{
	float yrd = yrot_delta;

	if (above)
		yrd *= 3.0;

	switch (key) {
		case GLUT_KEY_LEFT: // turn to the left
			yrot += yrd;
			break;
		case GLUT_KEY_RIGHT: // turn to the right
			yrot -= yrd;
			break;
		case GLUT_KEY_UP:
			if (above) // decrease height above maze
				birds_eye_height--;
			else // look up
				xrot -= xrot_delta;
			break;
		case GLUT_KEY_DOWN:
			if (above) // increase height above maze
				birds_eye_height++;
			else // look down
				xrot += xrot_delta;
			break;
	}
	glutPostRedisplay();
}

void motion(int x, int y)
{
	static const int centerx = WINDOW_WIDTH / 2.0;
	static const int centery = WINDOW_HEIGHT / 2.0;

	if (dont_grab_mouse)
		return;

	if (x == centerx && y == centery)
		return;

	glutWarpPointer(centerx, centery);

	if (!above)
		xrot -= (centery - y) * MOUSE_SENSITIVITY;
	yrot += (centerx - x) * MOUSE_SENSITIVITY;

	glutPostRedisplay();
}

void init_lighting()
{
	if (!do_lighting) {
		glDisable(GL_LIGHTING);
		return;
	}
	glEnable(GL_LIGHTING);
	glEnable(GL_LIGHT0);

	glLightfv(GL_LIGHT0, GL_POSITION, light_position);
	glLightfv(GL_LIGHT0, GL_DIFFUSE, light_diffuse);
	glLightfv(GL_LIGHT0, GL_AMBIENT, light_ambient);

	glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_TRUE);

	glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, mat_diffuse);
	glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, mat_ambient);
	glLightModelfv(GL_LIGHT_MODEL_AMBIENT, global_ambient);
}

void bind_texture(GLuint name, GLubyte *texels,
	unsigned long w, unsigned long h)
{
	glBindTexture(GL_TEXTURE_2D, name);
	glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_BLEND);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0,
		GL_RGB, GL_UNSIGNED_BYTE, texels);
}

void init_textures()
{
	GLubyte *texels = NULL;
	unsigned long w, h;
	int i;

	glGenTextures(NUM_TEXTURES, texture_names);
	for (i = 0; i < NUM_TEXTURES; i++) {
		load_bmp(texture_filenames[i], &texels, &w, &h);
		bind_texture(texture_names[i], texels, w, h);
		free(texels);
	}
}

void init_arrays()
{
	glEnableClientState(GL_VERTEX_ARRAY);
	glEnableClientState(GL_TEXTURE_COORD_ARRAY);
	glVertexPointer(2, GL_FLOAT, 0, square_vertices);
	glTexCoordPointer(2, GL_FLOAT, 0, tex_coords);
}

void init(void)
{
	srand(time(NULL));
    
	glMatrixMode(GL_MODELVIEW);
	glLoadIdentity();

    glEnable(GL_DEPTH_TEST);
	glEnable(GL_NORMALIZE);
	glShadeModel(GL_SMOOTH);

	// (0.561, 0.761, 0.929) is a sky blue
	glClearColor(0.561, 0.761, 0.929, 1.0);

	if (do_lighting) init_lighting();
	init_textures();
	init_arrays();

	ztrans_delta = CELL_SIZE / 15.0;
	xtrans_delta = ztrans_delta / 3.0;
	
	player_xpos = -GOALX * CELL_SIZE;
	player_zpos = -GOALY * CELL_SIZE;
	player_xpos = -STARTX * CELL_SIZE;
	player_zpos = -STARTY * CELL_SIZE;
	collision_check();

	init_cells();
	generate(GOALX, GOALY);

	cells[GOALX][GOALY] &= ~NORTH;

	start_time = glutGet(GLUT_ELAPSED_TIME);
	key_pressed('e', 0, 0); // enable display of elapsed time
}

int main(int argc, char **argv)
{
    glutInit(&argc, argv);
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH);
	glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT);
	glutInitWindowPosition(0, 0);
    glutCreateWindow("aMAZEing");
    glutDisplayFunc(display);
	glutReshapeFunc(reshape);
	glutKeyboardFunc(key_pressed);
	glutSpecialFunc(special_key_pressed);
	glutPassiveMotionFunc(motion);
	glutSetCursor(GLUT_CURSOR_NONE);
    init();
    glutMainLoop();
    return 0;
}

