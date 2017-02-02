TARGET = maze
SRC = maze.c
CFLAGS = -Wall
LIBS = -lGL -lGLU
OS = $(shell uname -s)

ifeq ($(OS),Darwin)
	CFLAGS += -framework GLUT -framework OpenGL -framework ApplicationServices
	CFLAGS += -L/System/Library/Frameworks/OpenGL.framework/Libraries -L/System/Library/Frameworks/GLUT.framework
	INCLUDE += -I/System/Library/Frameworks/GLUT.framework/Headers
	CFLAGS += -I/System/Library/Frameworks/ApplicationServices.framework/Frameworks/CoreGraphics.framework/Headers
else
ifeq ($(OS),Linux)
	INCLUDE += -I/usr/include/GL
	LIBS += -lglut -lm
endif
endif

$(TARGET): $(SRC)
	$(CC) $(SRC) $(CFLAGS) $(INCLUDE) $(LIBS) -o $(TARGET)

.PHONY: clean
clean:
	$(RM) $(TARGET)
