
# Import the pygame library and initialise the game engine
import pygame
import math
import random 
import pandas as pd

# Let's import the Paddle Class, Brick Class, the Ball Class and 
# the game settings
from paddle import Paddle
from ball import Ball
from brick import Brick
import settings

# game modes
PLAYER_MODE = 0 # regular player mode, game without RL
RL_MODE = 1     # game with RL, no player


game_mode = RL_MODE # current game mode
score = 0           # current score - number broken bricks
lives = 10000       # number of remained lives

successes_counter = 0
failures_counter = 0

# ============== Initialize the game ==============

# Initialize pygame library
pygame.init()
 
# Open a new window
size = (settings.WIDTH, settings.HEIGHT)
screen = pygame.display.set_mode(size)
pygame.display.set_caption("Bricks Breaker")
 
#This will be a list that will contain all the sprites we intend to use in our game.
all_sprites_list = pygame.sprite.Group()
 
# Create the Paddle
paddle = Paddle(settings.LIGHTBLUE, settings.PADDLE_LEN, settings.PADDLE_HEIGHT)
paddle.rect.x = 350
paddle.rect.y = settings.HEIGHT - settings.PADDLE_HEIGHT
 
# Create the ball sprite
ball = Ball(settings.WHITE, settings.BALL_RADIUS)
ball.rect.x = 345
ball.rect.y = 195

all_bricks = None
 
# Create bricks
def create_bricks():
    global all_bricks
    all_bricks = pygame.sprite.Group()
    for i in range(7):
        brick = Brick(settings.RED, settings.BRICK_LEN, settings.BRICK_HEIGHT)
        brick.rect.x = 60 + i * 100
        brick.rect.y = 60
        all_sprites_list.add(brick)
        all_bricks.add(brick)
    for i in range(7):
        brick = Brick(settings.ORANGE, settings.BRICK_LEN, settings.BRICK_HEIGHT)
        brick.rect.x = 60 + i * 100
        brick.rect.y = 100
        all_sprites_list.add(brick)
        all_bricks.add(brick)
    for i in range(7):
        brick = Brick(settings.YELLOW, settings.BRICK_LEN, settings.BRICK_HEIGHT)
        brick.rect.x = 60 + i * 100
        brick.rect.y = 140
        all_sprites_list.add(brick)
        all_bricks.add(brick)
        
create_bricks()
 
# Add the paddle to the list of sprites
all_sprites_list.add(paddle)
all_sprites_list.add(ball)
 
# The loop will carry on until the user exit the game (e.g. clicks the close button).
carryOn = True
 
# The clock will be used to control how fast the screen updates
clock = pygame.time.Clock()



# ============== Reinforsment Learning ==============

NUM_DEG = 180  # number of degrees
RL_INFO_PIX_SIZE = 40  # number of pixels in RL info
NUM_STATES = settings.WIDTH // settings.PADDLE_LEN # number of paddle states

# states of the RL info 
NOT_TESTED = 0
FAILED = -1
SUCCESS = 1

START_RL_AREA_Y = 170 # start RL area - end of the bricks area in y coordinate
END_RL_AREA_Y = settings.HEIGHT - settings.PADDLE_HEIGHT - settings.BALL_RADIUS # end RL area - start paddle

# number of the rows and columns of the RL area
RL_rows = (END_RL_AREA_Y - START_RL_AREA_Y) // RL_INFO_PIX_SIZE 
RL_cols = settings.WIDTH // RL_INFO_PIX_SIZE

# stages of one episode of RL
RL_NO_ACTIVITY = 0
RL_GET_RAND_Y = RL_NO_ACTIVITY + 1
RL_GET_RESULTS = RL_GET_RAND_Y + 1

# current episode state
rl_episode_state = RL_NO_ACTIVITY

# current RL info y (row) of the ball, that selected
# to snap the ball parameters (velocities, RL infos coordinates)
current_y_vel_ball_for_rl = 0

# snapped x, y RL infos coordinates and degrees of the ball
rl_info_x = 0
rl_info_y = 0
rl_info_deg = 0

# current selected state to be tested for the current 
# snapped x, y RL infos coordinates and degrees of the ball
rl_selected_state = 0


# dataframe to store the results of the RL
column_names = ["row", "col", "deg", "state", "res"]
processed_items_df = pd.DataFrame(columns = column_names)



# RL states. Each RL info object has 180 degrees and each degree has
# several paddle's states
class RL_States():
    
    def __init__(self):
        
        self.states = [NOT_TESTED] * NUM_STATES 
     
    # get state with success
    def get_success(self):
        if SUCCESS in self.states:
            return self.states.index(SUCCESS)
        return -1
    
    # get first state that is still not tested
    def get_not_tested(self):
        if NOT_TESTED in self.states:
            return self.states.index(NOT_TESTED)    # return first NOT TESTED state
        
        if SUCCESS not in self.states:              # if there is not SUCCESS state
            self.states = [NOT_TESTED] * NUM_STATES # initiate all the states with NOT TESTED
            return 0
        
        return -1
  
      
# RL info - small sub-area RL_INFO_PIX_SIZE x RL_INFO_PIX_SIZE in RL area
class RL_Info():
    # This class represents RL information
    
    def __init__(self):
        
        # create NUM_STATES (8) states, NUM_DEG (180) degrees for each state
        self.deg_states = [RL_States() for i in range(NUM_DEG) ]
        

# 2D array of RL infos 
RL_Table = [[RL_Info() for j in range(RL_cols)] for i in range(RL_rows)]



# return direction of the velocity (x,y) - angle between velocity
# vector and the x axis, positive direction is down
def get_direction(x, y):
    return int(math.degrees(math.atan2(y, x))) 


# get ball movement direction
def get_ball_direction():
    return get_direction(ball.velocity[0], ball.velocity[1])


# check if the ball is found in the RL area
def is_ball_in_RL_area():
    if ((ball.rect.y < END_RL_AREA_Y) and 
        (ball.rect.y > START_RL_AREA_Y)):
            return True;
    return False;


# get current y row in RL in which the ball is found 
def current_ball_rl_info_y_area():
    y = (ball.rect.y - START_RL_AREA_Y) // RL_INFO_PIX_SIZE
    if y < 0:
        y = 0
    elif y >= RL_rows:
        y = RL_rows - 1
    return y


# get current x row in RL in which the ball is found 
def current_ball_rl_info_x_area():
    x = ball.rect.x // RL_INFO_PIX_SIZE
    if x < 0:
        x = 0
    elif x >= RL_cols:
        x = RL_cols - 1
    return x


# check if the ball is found in the RL area 
# and has a positive direction (down)
def is_ball_in_RL_area_and_positive_dir():
    if is_ball_in_RL_area() == True and get_ball_direction() > 0:
        return True
    return False


# get random y row in RL in certain range
def get_rand_rl_info_y():
    current_ball = current_ball_rl_info_y_area()
    return random.randint(current_ball + 1, current_ball + 2) 


# save RL results in the file 'Results.csv'
def save_results():
    global processed_items_df
    # remove duplicated rows from the data frame
    processed_items_df.drop_duplicates(subset = column_names, keep = "first", inplace = True)
    processed_items_df.to_csv(r'Results.csv', index = False)
    

# load RL results from the file 'Results.csv'
def load_results():
    global processed_items_df
    processed_items_df.drop(processed_items_df.index, inplace=True) # clear current data
    processed_items_df = pd.read_csv(r'Results.csv')
    for i, row in processed_items_df.iterrows(): # pass all the rows
        # and set the data to 'RL_Table'
        RL_Table[row["row"]][row["col"]].deg_states[row["deg"]].states[row["state"]] = row["res"]
    

# ---------- Debug functions -------------------------
# These functions are used for debugging only
    
def debug_add_to_processed_items_list(result):
    global processed_items_df
 
    new_df_row = [rl_info_y, rl_info_x, rl_info_deg, rl_selected_state, result]
    processed_items_df.loc[len(processed_items_df)] = new_df_row
    text = "row: " + str(rl_info_y) + " col: " + str(rl_info_x) + " deg: " + str(rl_info_deg) + " state: " + str(rl_selected_state) + " res: " + str(result)
    print("\n", text, "\n")
    text = "Successes: " +  str(successes_counter) + ", Failures: " + str(failures_counter)
    print("\n", text, "\n")
    
    
def debug_current_rl_common_state():
    print("\nCurrent RL state:", rl_episode_state)
    print(" - ball:", "rect - ", ball.rect.x, ball.rect.y,
          "velocity - ", ball.velocity[0], 
          ball.velocity[1], "dir - ", get_ball_direction())
    if is_ball_in_RL_area():
        print(" - current_ball_rl_info_y_area:", current_ball_rl_info_y_area())
    else:
        print(" - Ball is not in RL area")
    print("\n")
    
    
def debug_rl_no_activity():
    print("rl_episode_state = RL_NO_ACTIVITY")
    print(" - ball:", "rect - ", ball.rect.x, ball.rect.y, "y info area - ", current_ball_rl_info_y_area(),
          "velocity - ", ball.velocity[0], 
          ball.velocity[1], "dir - ", get_ball_direction())
    print(" - current_y_vel_ball_for_rl:", current_y_vel_ball_for_rl)
    
    
def debug_rl_get_rand_y_1():
    print("rl_episode_state = RL_GET_RAND")
    print(" - rl_info_x", rl_info_x)
    print(" - rl_info_y", rl_info_y)
    print(" - rl_info_deg", rl_info_deg)
    
    
def debug_rl_get_rand_y_2():
    print(" - rl_selected_state", rl_selected_state)
    
    
def debug_get_results():
    print("rl_episode_state = RL_GET_RESULTS")
    print(" - paddle:", paddle.rect.x)
    

# ============== Main Program Loop ==============

load_results() # load of RL results
while carryOn:
    # --- Main event loop
    
    for event in pygame.event.get(): # User did something
        if event.type == pygame.QUIT: # If user clicked close
            carryOn = False # Flag that we are done so we exit this loop
    
    # player mode - user moves the paddle, no RL 
    if game_mode == PLAYER_MODE:    
        #Moving the paddle when the use uses the arrow keys
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            paddle.moveLeft(settings.MOVE_PADDLE_VELOCITY)
        if keys[pygame.K_RIGHT]:
            paddle.moveRight(settings.MOVE_PADDLE_VELOCITY)
            
    # RL mode - the paddle learns to play without a user
    else:     
        #debug_current_rl_common_state()
        # if no RL activity state and the ball entered into RL area and its direction is down
        if rl_episode_state == RL_NO_ACTIVITY and is_ball_in_RL_area() == True and get_ball_direction() > 0:
            # get a random y RL info coordinate
            current_y_vel_ball_for_rl = get_rand_rl_info_y()
            # go to the next RL state
            rl_episode_state = RL_GET_RAND_Y
            #debug_rl_no_activity()
        
        # the second RL activity state - get the current y RL info coordinate of the ball
        # and if it is equal to the random y RL info coordinate, recieved in the previous state
        # get the current ball location and its direction
        elif rl_episode_state == RL_GET_RAND_Y and current_ball_rl_info_y_area() == current_y_vel_ball_for_rl:
            rl_info_x = current_ball_rl_info_x_area()        # get x RL info of the ball
            rl_info_y = current_ball_rl_info_y_area()        # get y RL info of the ball
            rl_info_deg = get_ball_direction()               # get the ball direction
            #debug_rl_get_rand_y_1()
            
            # select the paddle state for testing
            rl_episode_state = RL_GET_RESULTS
            # if a succeses case exists choose it
            rl_selected_state = RL_Table[rl_info_y][rl_info_x].deg_states[rl_info_deg].get_success()
            # if it is no succesfull state
            if rl_selected_state == -1: 
                # find the first case that has not been tested yet
                rl_selected_state = RL_Table[rl_info_y][rl_info_x].deg_states[rl_info_deg].get_not_tested()
                if rl_selected_state == -1: # no not tested
                    rl_episode_state = RL_NO_ACTIVITY
            #debug_rl_get_rand_y_2()
         
        # the third RL activity state get results of the chosen paddle state
        # move the paddle to the choosen state
        elif rl_episode_state == RL_GET_RESULTS:
            if paddle.rect.x < (rl_selected_state * settings.PADDLE_LEN):
                paddle.moveRight(settings.MOVE_PADDLE_VELOCITY)
            elif paddle.rect.x > (rl_selected_state * settings.PADDLE_LEN):
                paddle.moveLeft(settings.MOVE_PADDLE_VELOCITY)
            #debug_get_results()
            
 
    # --- Game logic should go here
    all_sprites_list.update()
 
    #Check if the ball is bouncing against any of the 4 walls:
    if ball.rect.x >= (settings.WIDTH - settings.BALL_RADIUS):
        ball.velocity[0] = -ball.velocity[0]
    elif ball.rect.x <= 0:
        ball.velocity[0] = -ball.velocity[0]
        
    if ball.rect.y <= settings.BALL_RADIUS:
        ball.velocity[1] = -ball.velocity[1]
    elif ball.rect.y >= (settings.HEIGHT - settings.BALL_RADIUS):
        ball.velocity[1] = -ball.velocity[1]
        lives -= 1
        # the paddle missed the ball 
        if rl_episode_state == RL_GET_RESULTS:
          # update RL_Table with 'failed' result
          if RL_Table[rl_info_y][rl_info_x].deg_states[rl_info_deg].states[rl_selected_state] == NOT_TESTED:
              RL_Table[rl_info_y][rl_info_x].deg_states[rl_info_deg].states[rl_selected_state] = FAILED
          rl_episode_state = RL_NO_ACTIVITY
          failures_counter += 1
          debug_add_to_processed_items_list(FAILED)
        if lives == 0:
            #Display Game Over Message for 3 seconds
            font = pygame.font.Font(None, 74)
            text = font.render("GAME OVER", 1, settings.WHITE)
            screen.blit(text, (250,300))
            pygame.display.flip()
            pygame.time.wait(3000)
 
            # Stop the Game
            carryOn=False
 
    # Detect collisions between the ball and the paddles
    if pygame.sprite.collide_mask(ball, paddle):
      ball.rect.x -= ball.velocity[0]
      ball.rect.y = settings.HEIGHT - settings.BALL_RADIUS - settings.PADDLE_HEIGHT
      ball.velocity[1] = -ball.velocity[1]
      # the paddle captured the ball
      if rl_episode_state == RL_GET_RESULTS:
          # update RL_Table with 'success' result
          RL_Table[rl_info_y][rl_info_x].deg_states[rl_info_deg].states[rl_selected_state] = SUCCESS
          rl_episode_state = RL_NO_ACTIVITY
          successes_counter += 1
          debug_add_to_processed_items_list(SUCCESS)
      
 
    # Check if there is a car collision
    brick_collision_list = pygame.sprite.spritecollide(ball, all_bricks, False)
    for brick in brick_collision_list:
      ball.bounce()
      score += 1
      brick.kill()
      if len(all_bricks)==0:
           #Display Level Complete Message for 3 seconds
            font = pygame.font.Font(None, 74)
            text = font.render("LEVEL COMPLETE", 1, settings.WHITE)
            screen.blit(text, (200,300))
            pygame.display.flip()
            pygame.time.wait(3000)
            
            create_bricks()
            ball.rect.x = 345
            ball.rect.y = 195
 
            #Stop the Game
            carryOn=True
 
    # --- Drawing code should go here
    # First, clear the screen to dark blue.
    screen.fill(settings.DARKBLUE)
    pygame.draw.line(screen, settings.WHITE, [0, 38], [800, 38], 2)
 
    # Display the score and the number of lives at the top of the screen
    font = pygame.font.Font(None, 34)
    text = font.render("Score: " + str(score), 1, settings.WHITE)
    screen.blit(text, (20,10))
    text = font.render("Lives: " + str(lives), 1, settings.WHITE)
    screen.blit(text, (650,10))
 
    # Now let's draw all the sprites in one go. (For now we only have 2 sprites!)
    all_sprites_list.draw(screen)
 
    # --- Go ahead and update the screen with what we've drawn.
    pygame.display.flip()
 
    # --- Limit to 60 frames per second
    clock.tick(settings.FPS)
 
    
# Once we have exited the main program loop we can stop the game engine:
pygame.quit()


