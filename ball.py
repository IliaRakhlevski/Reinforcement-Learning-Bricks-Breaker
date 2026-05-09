import pygame
import settings
from random import randint
 

# minimal and maximal valocity values for x and y coordinates
MIN_VELOCITY = 3
MAX_VELOCITY = 5
 
class Ball(pygame.sprite.Sprite):
    # This class represents a car. It derives from the "Sprite" class in Pygame.
    
    def __init__(self, color, radius):
        # Call the parent class (Sprite) constructor
        super().__init__()
        
        # Pass in the color of the car, and its x and y position, width and height.
        # Set the background color and set it to be transparent
        self.image = pygame.Surface([radius, radius])
        self.image.fill(settings.BLACK)
        self.image.set_colorkey(settings.BLACK)
 
        # Draw the ball
        pygame.draw.circle(self.image, color, (radius // 2, radius // 2), radius // 2)
        
        self.velocity = [randint(MIN_VELOCITY, MAX_VELOCITY), randint(-MAX_VELOCITY, MAX_VELOCITY)]
        if self.velocity[1] == 0: # y - velocity cannot be 0
            self.velocity[1] = 1
        
        # Fetch the rectangle object that has the dimensions of the image.
        self.rect = self.image.get_rect()
     
    # move the ball accordint to the current velocity
    def update(self):
        self.rect.x += self.velocity[0]
        self.rect.y += self.velocity[1]
     
    # set a new velocity
    def bounce(self):
        # x - coordinate velocity: change sign of this velocity
        self.velocity[0] = -self.velocity[0]
        # y - coordinate velocity: get random
        self.velocity[1] = randint(-MAX_VELOCITY, MAX_VELOCITY)
        if self.velocity[1] == 0: # y - velocity cannot be 0
            self.velocity[1] = 1