import numpy as np
import pyglet
import random
import time
import matplotlib.pyplot as plt
from math import radians, degrees

MAX_OBJ_LIMIT = 105 # in mm
MIN_OBJ_LIMIT = 25  # in mm
obj_loc = np.array([]) # object position

# tl : theta_left
# dl : distance from object base to left finger base
# tr : theta_right
# dr : distance from object base to right finger base

class FFEnv(object):
    viewer = None
    dt = 0.01    # refresh rate
    action_bound = [-1, 1]
    state_size = 7
    action_size = 2
    center_coord = np.array([100, 0])

    w0 = 25  # Object width
    wp = 50  # 
    fw = 18  # Finger width

    def __init__(self):
        self.ff_info = np.zeros(2, dtype=[('d', np.float32), ('t', np.float32), ('a', np.int)])
        self.goal = {'x': 0., 'y': 0., 'w':self.w0} # Goal Position of the Object 
        self.goal['x'], self.goal['y'] = self.get_goal_point()
        # Intialising with sliding on left finger 
        self.ff_info['t'][1] = radians(90)     # Initialising tr in deg
        self.ff_info['d'][1] =  35             # Initialising dr in mm
        self.ff_info['t'][0], self.ff_info['d'][0] = self.calc_left_config(self.ff_info['t'][1], self.ff_info['d'][1])
        self.obj_pos = {'x':0., 'y':0.} # Object Position
        self.on_goal = 0
        
        # Initialising with sliding on right finger
        #self.ff_info['t'][0] = radians(90)      # Initialising tl in deg
        #self.ff_info['d'][0] = 105                # Initialising dl in mm
        #self.ff_info['t'][1], self.ff_info['d'][1] = self.calc_right_config(self.ff_info['t'][0], self.ff_info['d'][0])

        self.ff_info['a'] = 0
        #print('Initial ff_info : ', self.ff_info)
        
    def step(self, action):
        done = False
        # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        # action : Check the action taken ( left or right )
        # action[0] != 0 (action is left)
        # action[1] != 0 (action is right)
        # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        #print('raw action : ', action)
        print("action from agent : ", action)
        if (action[0] != 0 and action[1] == 0): # Action is sliding on left finger
            print("Action sliding Left")
            self.ff_info['a'][0] = 1 
            self.ff_info['a'][1] = 0
            # Creating dummy variables t0, d0, t1, d1
            self.t1 = self.ff_info['t'][1]
            self.d1 = self.ff_info['d'][1]
            
            self.t1 += action[0] * self.dt # Adding the action delta theta to theta_right or t_r

            # Constraining the right finger 
            if (self.t1 < radians(40)):   # limit it to greater than 40 deg
                action[0] = 0 
                print("Crossing limits t1 < 40")
            if (self.d1 >= MAX_OBJ_LIMIT):   # limit it to 105 mm 
                action[0] = 0 
                print("Crossing limits d1 > 105")
            if (self.d1 <= MIN_OBJ_LIMIT):    # limit it to 25 mm
                action[0] = 0 
                print("Crossing limits d1 < 25")

            # Getting tl, dl by giving tr, dr
            self.t0, self.d0 = self.calc_left_config(self.t1, self.d1) 

            # Constraining tl, dl limits  
            if (self.d0 >= MAX_OBJ_LIMIT): # Maximum limit
                action[0] = 0
                print("Crossing limits d0 > 105")
            if (self.d0 <= MIN_OBJ_LIMIT): # limit it to 25 mm
                action[0] = 0 
                print("Crossing limits d0 < 25")
            if (self.t0 >= radians(140)):  # limit t0 at 140 deg
                action[0] = 0
                print("Crossing limits t0 > 140")

            if (action[0] == 0):
                print("Crossing limits so action[0] = 0")    
            
            elif (action[0] != 0):
                print("Action taken")
                action[0] = np.clip(action[0], *self.action_bound) # Clipping the action
                self.ff_info['t'][1] += action[0] * self.dt # Adding the action delta theta to theta_right or t_r
                #self.ff_info['t'][1] %= np.pi * 2 # normalize ! Why ? Need to know
                print('delta theta : [', action[0] * self.dt, ', ', action[1], ']')
                # Getting tl, dl by giving tr, dr
                self.ff_info['t'][0], self.ff_info['d'][0] = self.calc_left_config(self.ff_info['t'][1], self.ff_info['d'][1])   
        
        elif (action[1] != 0 and action[0] == 0): # Action is sliding on right finger
            print("Action Sliding Right")
            self.ff_info['a'][0] = 0 
            self.ff_info['a'][1] = 1
            # Creating dummy variables t0, d0, t1, d1
            self.t0 = self.ff_info['t'][0]
            self.d0 = self.ff_info['d'][0]

            action[1] = np.clip(action[1], * self.action_bound) # Clipping the action
            self.t0 += action[1] * self.dt # Adding the action delta theta to theta_right or t_r

            # Constraining the left finger to lesser than 140 deg
            if ( self.t0 >= radians(140) ):
                action[1] = 0
                print("Crossing limits t0 >= 140")
            if (self.d0 >= MAX_OBJ_LIMIT ):
                action[1] = 0
                print("Crossing limits d0 >= 105")
            if (self.d0 <= MIN_OBJ_LIMIT):
                action[1] = 0
                print("Crossing limits d0 <= 25")

            # Getting tr, dr by giving tl, d1
            self.t1, self.d1 = self.calc_right_config(self.t0, self.d0)

            # Constraining t1, d1 limits
            if ( self.d1 >= MAX_OBJ_LIMIT ):
                action[1] = 0
                print("Crossing limits d1 >= 105")
            if (self.d1 <= MIN_OBJ_LIMIT):
                action[1] = 0
                print("Crossing limits d1 <= 25")
            if ( self.t1 <= radians(40) or self.t1 >= radians(152) ): # greater than 140 deg
                action[1] = 0
                print("Crossing limits t1 <= 40")

            if (action[1] == 0):
                print(" So action[1] = 0") 

            if (action[1] != 0):
                print("Action taken")
                # For sliding right take action for t0 and get tr, dr
                self.ff_info['t'][0] += action[1] * self.dt  
                #self.ff_info['t'][1] %= np.pi * 2 # normalize ! Why ? Need to know         
                print('delta theta : [', action[0], ', ', action[1]* self.dt, ']')
                # Getting tl, dl by giving tr, dr
                self.ff_info['t'][1], self.ff_info['d'][1] = self.calc_right_config(self.ff_info['t'][0], self.ff_info['d'][0]) 

        #print('ff_info : ', self.ff_info)
        # For only sliding on left finger code we no need use ff_info['a']
        # State        
        # Object Position
        # There is a difference in slide_obj_right and slide_obj_left. Let's follow a standard of slide_obj_right
        self.obj_pos['x'], self.obj_pos['y'] = self.get_obj_slide_right(self.ff_info['t'][0], self.ff_info['d'][0])  
        
        # Distance from goal to object
        dist_x = self.obj_pos['x'] - self.goal['x'] 
        dist_y = self.obj_pos['y'] - self.goal['y']
        
        # done and reward
        #print("dist_x :", dist_x)
        #print("dist_y :", dist_y)
        reward = -np.sqrt(dist_x**2 + dist_y**2)
        #r = 0. # Sparse reward Calculate distance between obj_pos and goal_pos
        
        # Check if object is near to goal in x-axis
        if ( self.goal['x'] - self.goal['w']/2 < self.obj_pos['x'] < self.goal['x'] - self.goal['w']/2 ):
            # Check if object is near to goal in y-axis
            if ( self.goal['y'] - self.goal['w']/2 < self.obj_pos['y'] < self.goal['y'] - self.goal['w']/2 ):
                reward +=1.
                self.on_goal += 1
                if self.on_goal > 50:
                    done = True
        else:
            self.on_goal = 0

        # Concatenate and normalize
        state = np.concatenate((self.ff_info['t'][0], self.ff_info['t'][1], self.obj_pos['x']/200, self.obj_pos['y']/200, dist_x/200, dist_y/200, [1. if self.on_goal else 0.]), axis=None)
        #print("state -> step(action): ", state)
        print('ff_info : ', self.ff_info)
        
        return state, reward, done
    
    def reset(self):
        # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        # During start of every episode the agent will reset the environment 
        # 1. Gives a new goal location
        # 2. Gives a initial state of the system 
        #
        # Input : none
        # Output : state
        # State : { theta_l, theta_r, d_l, d_r, O_x, O_y, (G-O)_x, (G-O)_y, done }
        self.ff_info['t'][0] = radians(90)
        self.ff_info['d'][0] = 100
        self.ff_info['t'][1], self.ff_info['d'][1] = self.calc_right_config(self.ff_info['t'][0], self.ff_info['d'][0])
        
        # Goal location 
        self.goal['x'], self.goal['y'] = self.get_goal_point()
        
        # Object Position
        # There is a difference in slide_obj_right and slide_obj_left. Let's follow a standard of slide_obj_right
        self.obj_pos['x'], self.obj_pos['y'] = self.get_obj_slide_right(self.ff_info['t'][0], self.ff_info['d'][0])        
        #obj_pos_slide_left = self.get_obj_slide_left(self.ff_info['t'][1], self.ff_info['d'][1])

        #print("Obj Center while sliding right : ", self.obj_pos)
        #print("Obj Center while sliding left : ", obj_pos_slide_left)

        # Distance from goal to object
        dist_x = self.obj_pos['x'] - self.goal['x'] 
        dist_y = self.obj_pos['y'] - self.goal['y']

        state = np.concatenate((self.ff_info['t'][0], self.ff_info['t'][1], self.obj_pos['x']/200, self.obj_pos['y']/200, dist_x/200, dist_y/200, [1. if self.on_goal else 0.]), axis=None)
        #print("state : ", state)
        return state

    def render(self):
        if self.viewer is None:
            self.viewer = Viewer(self.ff_info, self.goal)
        self.viewer.render()
        print('===============x================x====================x====================')

    def calc_left_config(self, tr, dr):
        d2v = np.array([dr * np.cos(np.float64(tr)), dr * np.sin(np.float64(tr))])
        w0v = np.array([self.w0 * np.sin(np.float64(tr)), -self.w0 * np.cos(np.float64(tr))])
        wpv = np.array([self.wp, 0.])
        f1v = np.array([self.fw * np.sin(np.float64(tr)), -self.fw * np.cos(np.float64(tr))])
        av = d2v - f1v - w0v + wpv
        # Calculate of thetal, dl
        dl = np.sqrt(float((av * av).sum() - self.fw * self.fw))
        tl = np.arctan2(float(av[1]), float(av[0])) + np.arctan2(self.fw, dl)
        return tl, dl

    def calc_right_config(self, tl, dl):
        d1v = np.array([dl * np.cos(tl), dl * np.sin(tl)])
        d1v = d1v.reshape(1,2)[0]
        w0v = np.array([self.w0 * np.sin(tl), -self.w0 * np.cos(tl)])
        w0v = w0v.reshape(1,2)[0]
        wpv = np.array([self.wp, 0.])
        f1v = np.array([self.fw * np.sin(tl), -self.fw * np.cos(tl)])
        f1v = f1v.reshape(1,2)[0]
        av = d1v + w0v + f1v - wpv
        # Calculate thetar, dr
        dr = np.sqrt(float((av * av).sum() - self.fw * self.fw))
        tr = np.arctan2(float(av[1]), float(av[0])) - np.arctan2(self.fw, dr)
        return tr, dr

    def sample_action(self):
        list_ = [0, 1]                        # Create a list of [0, 1] [left, right]
        list_i = random.choice(list_)         # Randomly select from list_
        action_i = np.random.rand(1) - 0.5    # Take a random action
        action = np.zeros(2)                  # Initialising actions with zeros  
        print('Sampled an action')
        if (list_i == 0):                       
            action[0] = action_i
        else:
            action[1] = action_i
        print('action :', action)
        return action
  
    # Additional function
    def slope(self,x1, y1, x2, y2):
        m = float(float((y2 - y1))/float((x2 - x1)))
        return m

    # Additional function
    def get_goal_point(self):  
        goal_flag = True
        while (goal_flag):
            # Defining Points from A - D 
            D_x, D_y = (-137.71, 215.09)
            E_x, E_y = (45.107, 284.509)
            F_x, F_y = (76.249, 281.25)
            A_x, A_y = (243.11, 210.22)
            B_x, B_y = (112.96, 129.67)
            C_x, C_y = (-22.80, 118.67)

            # Randomly selecting X, Y-Co-ordinates of goal within limits
            x_g = np.random.randint(-137.71, 243.11, size=1).astype("float64")
            y_g = np.random.randint(118.67, 284.80, size=1).astype("float64")

            # Then sort it based on the section 
            if (-137.70 < x_g < -22.80):
                section = 1
            elif (-22.80 <= x_g < 45.07):
                section = 2
            elif (45.07 <= x_g < 76.249):
                section = 3
            elif (76.249 <= x_g < 112.96):
                section = 4
            elif (112.96 <= x_g < 243.11):
                section = 5

            if (section == 1):
                # slope of point G and point C
                m_gc = self.slope(C_x, C_y, x_g, y_g)
                # Slope of line CD
                m_cd = self.slope(C_x, C_y, D_x, D_y)
                # Slope of line DE
                m_de = self.slope(D_x, D_y, E_x, E_y)
                # Slope of point G and point D
                m_gd = self.slope(D_x, D_y, x_g, y_g)
                if (m_gd > m_cd and m_gd < m_de):
                    #print("Yes It is inside the Section- I limits")
                    goal_flag = False
                    
            elif (section == 2):
                # Slope of line CB
                m_cb = self.slope(C_x, C_y, B_x, B_y)
                # Slope of line DE
                m_de = self.slope(D_x, D_y, E_x, E_y)
                # Slope of point G and point C
                m_gc = self.slope(C_x, C_y, x_g, y_g)
                # Slope of point G and point D
                m_gd = self.slope(D_x, D_y, x_g, y_g)
                if (m_gc > m_cb and m_gd < m_de):
                    #print("Yes It is inside the Section- II limits")
                    goal_flag = False
                    
            elif (section == 3):
                # Slope of line CB
                m_cb = self.slope(C_x, C_y, B_x, B_y)
                # Slope of line FE
                m_fe = self.slope(F_x, F_y, E_x, E_y)
                # Slope of point G and point C
                m_gc = self.slope(C_x, C_y, x_g, y_g)
                # Slope of point G and point E
                m_ge = self.slope(E_x, E_y, x_g, y_g)
                if (m_gc > m_cb and m_ge < m_fe):
                    #print("Yes It is inside the Section III limits")
                    goal_flag = False
                    
            elif (section == 4):
                # Slope of line CB
                m_cb = self.slope(C_x, C_y, B_x, B_y)
                # Slope of line FA
                m_fa = self.slope(F_x, F_y, A_x, A_y)
                # Slope of point G and point F
                m_gf = self.slope(F_x, F_y, x_g, y_g)
                # Slope of point G and point C
                m_gc = self.slope(C_x, C_y, x_g, y_g)
                if (m_gc > m_cb and m_gf < m_fa):
                    #print("Yes It is inside the Section IV limits")
                    goal_flag = False        
                    
            elif (section == 5):
                # Slope of line AB
                m_ab = self.slope(A_x, A_y, B_x, B_y)
                # Slope of line FA
                m_fa = self.slope(F_x, F_y, A_x, A_y)
                # Slope of point G and point F
                m_gf = self.slope(F_x, F_y, x_g, y_g)
                # Slope of point G and point B
                m_gb = self.slope(B_x, B_y, x_g, y_g)
                if (m_gf < m_fa and m_gb > m_ab):
                    #print("Yes It is inside the limits")
                    goal_flag = False
                    
            #print("goal :", x_g, y_g )
            if (goal_flag == False):
                return x_g, y_g
    
    # Additional function
    def get_obj_slide_right(self,tl, dl):
        x_square = (dl + self.w0 / 2.) * np.cos(tl) + (self.w0 / 2. + self.fw) * np.sin(tl) # x_sq (Center of the object)
        y_square = (dl + self.w0 / 2.) * np.sin(tl) - (self.w0 / 2. + self.fw) * np.cos(tl) # y_sq (Center of the object)
        x_square = x_square*2.5 + self.center_coord[0]*2 
        y_square = y_square*2.5
        return x_square, y_square    # *2.5 for scaling up output
    
    # Additional function
    def get_obj_slide_left(self,tr, dr):
        x_square = self.wp + (dr + self.w0 / 2.) * np.cos(np.float64(tr)) - (self.fw + self.w0 / 2.) * np.sin(np.float64(tr)) 
        y_square = (dr + self.w0 / 2.) * np.sin(np.float64(tr)) + (self.fw + self.w0 / 2.) * np.cos(np.float64(tr))
        obj_center = np.array([x_square, y_square])
        obj_center = obj_center*2.5
        obj_center += self.center_coord
        return obj_center    # *2.5 for scaling up output

class Viewer(pyglet.window.Window):
    w0 = 25  # Object width
    wp = 50  # 
    fw = 18  # Finger width
    obj_loc = []

    def __init__(self, ff_info, goal):
        # vsync=False to not use the monitor FPS, we can speed up training
        super(Viewer, self).__init__(width=500, height=500, resizable=False, caption='FrictoinFinger', vsync=False)
        pyglet.gl.glClearColor(1, 1, 1, 1)
        self.ff_info = ff_info
        self.center_coord = np.array([100, 0]) 

        self.obj_pos, self.obj_center = self.slide_Left_obj(self.ff_info['t'][1], self.ff_info['d'][1]) 
        self.finger_l, self.finger_r = self.slide_Left_fingers(self.ff_info['t'][1], self.ff_info['d'][1]) 

        self.batch = pyglet.graphics.Batch()  # display whole batch at once
        
        # Object Position
        self.object = self.batch.add(
            4, pyglet.gl.GL_QUADS, None,    # 4 corners
            ('v2f', [self.obj_pos[1][0], self.obj_pos[1][1],     
                     self.obj_pos[0][0], self.obj_pos[0][1],
                     self.obj_pos[3][0], self.obj_pos[3][1],
                     self.obj_pos[2][0], self.obj_pos[2][1]]),
            ('c3B', (138, 43, 226) * 4))    # color
        # Left Finger
        self.finger_l = self.batch.add(
            4, pyglet.gl.GL_QUADS, None,
            ('v2f', [self.finger_l[3][0], self.finger_l[3][1],
                     self.finger_l[2][0], self.finger_l[2][1],
                     self.finger_l[1][0], self.finger_l[1][1],
                     self.finger_l[0][0], self.finger_l[0][1]]),
            ('c3B', (255, 215, 0) * 4,))    # color
        # Right finger
        self.finger_r = self.batch.add(
            4, pyglet.gl.GL_QUADS, None,
            ('v2f', [self.finger_r[3][0], self.finger_r[3][1],
                     self.finger_r[2][0], self.finger_r[2][1],
                     self.finger_r[1][0], self.finger_r[1][1],
                     self.finger_r[0][0], self.finger_r[0][1] ]),
                     ('c3B', (255, 215, 0) * 4,))
        # Goal Position of the object
        self.goal_pos = self.batch.add(
            4, pyglet.gl.GL_QUADS, None,
            ('v2f', [goal['x']+20, goal['y']+20,
                     goal['x']+20, goal['y']-20,
                     goal['x']-20, goal['y']-20,
                     goal['x']-20, goal['y']+20 ]),
                     ('c3B', (124, 252, 0) * 4,))
        #print("obj_pos : ", self.obj_pos)
        #print("obj_goal : ", self.obj_goal)             
        #print("goal pos : ", goal['x'], goal['y'])
        #obj_loc = np.array([self.obj_center])

    def slide_Left_obj(self,tr, dr):
        # Define :  slide the object on left finger with friction enabled on right finger and disabled on left finger
        # Input : t_right, d_right
        # Output : t_left, d_left

        # Transformation Matrix
        x_square = self.wp + (dr + self.w0 / 2.) * np.cos(np.float64(tr)) - (self.fw + self.w0 / 2.) * np.sin(np.float64(tr)) 
        y_square = (dr + self.w0 / 2.) * np.sin(np.float64(tr)) + (self.fw + self.w0 / 2.) * np.cos(np.float64(tr))
        pts = np.array([[-self.w0 / 2., -self.w0 / 2., self.w0 / 2., self.w0 / 2.], [-self.w0 / 2., self.w0 / 2., self.w0 / 2., -self.w0 / 2.], [1, 1, 1, 1]])
        R = np.array([[np.cos(tr), -np.sin(tr), x_square], [np.sin(tr), np.cos(tr), y_square], [0, 0, 1]])
        
        # Points after transformation
        pts_new = np.dot(R, pts)
        
        # Plotting the Object
        pts = np.transpose([[pts_new[0, :]], [pts_new[1, :]]])
        pts = pts.reshape((4, 2))
        obj_center = np.array([x_square, y_square])
        return pts*2.5, obj_center*2.5 # *2.5 for scaling up output

    def slide_Left_fingers(self,tr, dr):
        
        # Calculate thetar, dr
        d2v = np.array([dr * np.cos(np.float64(tr)), dr * np.sin(np.float64(tr))])
        w0v = np.array([self.w0 * np.sin(np.float64(tr)), -self.w0 * np.cos(np.float64(tr))])
        wpv = np.array([self.wp, 0.])
        f1v = np.array([self.fw * np.sin(np.float64(tr)), -self.fw * np.cos(np.float64(tr))])
        av = d2v - f1v - w0v + wpv
        
        # Calculated Values of theta1, dl
        dl = np.sqrt(float((av * av).sum() - self.fw * self.fw))
        tl = np.arctan2(float(av[1]), float(av[0])) + np.arctan2(self.fw, dl)
        l_fw_pts = np.array([[0., 0., self.fw, self.fw], [10, 130, 130, 10], [1.0, 1.0, 1.0, 1.0]])
        r_fw_pts = np.array([[0., 0., -self.fw, -self.fw], [10, 130, 130, 10], [1.0, 1.0, 1.0, 1.0]])
        
        # Transformation matrices for the finger width
        R_fw1 = [[np.cos(tl - np.pi / 2.0), -np.sin(tl - np.pi / 2), 0.0], [np.sin(tl - np.pi / 2), np.cos(tl - np.pi / 2), 0.0], [0.0, 0.0, 1.0]]
        R_fw2 = [[np.cos(tr - np.pi / 2), -np.sin(tr - np.pi / 2), self.wp], [np.sin(tr - np.pi / 2), np.cos(tr - np.pi / 2), 0.0], [0.0, 0.0, 1.0]]
        
        # finger Coordinates 1-> Left, 2-> Right
        pts_fw1 = np.dot(R_fw1, l_fw_pts)
        pts_fw2 = np.dot(R_fw2, r_fw_pts)
        
        # Plotting the fingers
        fw_1 = np.transpose([[pts_fw1[0, :]], [pts_fw1[1, :]]]).reshape((4, 2))
        fw_2 = np.transpose([[pts_fw2[0, :]], [pts_fw2[1, :]]]).reshape((4, 2))
        
        return fw_1*2.5, fw_2*2.5 # *2.5 for scaling up output

    def slide_Right_obj(self,tl, dl):
        # Define :  slide the object on right finger with friction enabled on left finger and disabled on right finger
        # Input : t_left, d_left
        # Output : t_right, d_right
        
        # Transformation Matrix
        x_square = (dl + self.w0 / 2.) * np.cos(tl) + (self.w0 / 2. + self.fw) * np.sin(tl) # x_sq (Center of the object)
        y_square = (dl + self.w0 / 2.) * np.sin(tl) - (self.w0 / 2. + self.fw) * np.cos(tl) # y_sq (Center of the object)
        pts = np.array([[-self.w0 / 2., -self.w0 / 2., self.w0 / 2., self.w0 / 2.], [-self.w0 / 2., self.w0 / 2., self.w0 / 2., -self.w0 / 2.], [1, 1, 1, 1]])
        R = np.array([[np.cos(tl), -np.sin(tl), x_square], [np.sin(tl), np.cos(tl), y_square], [0, 0, 1]])
        print("dl : ", dl)
        # Points after transformation
        pts_new = np.dot(R, pts)
        
        # Plotting the Object
        pts = np.transpose([[pts_new[0, :]], [pts_new[1, :]]])
        pts = pts.reshape((4, 2))
        obj_center = np.array([x_square, y_square])
    
        return pts*2.5, obj_center*2.5 # *2.5 for scaling up output

    def slide_Right_fingers(self, tl, dl):
        
        # Calculate theta1, dl
        d1v = np.array([dl * np.cos(tl), dl * np.sin(tl)])
        w0v = np.array([self.w0 * np.sin(tl), -self.w0 * np.cos(tl)])
        wpv = np.array([self.wp, 0.])
        f1v = np.array([self.fw * np.sin(tl), -self.fw * np.cos(tl)])
        av = d1v + w0v + f1v - wpv
        
        # Calculated Values of thetar, dr
        dr = np.sqrt(float((av * av).sum() - self.fw * self.fw))
        tr = np.arctan2(float(av[1]), float(av[0])) - np.arctan2(self.fw, dr)

        l_fw_pts = np.array([[0., 0., self.fw, self.fw], [10, 130, 130, 10], [1.0, 1.0, 1.0, 1.0]])
        r_fw_pts = np.array([[0., 0., -self.fw, -self.fw], [10, 130, 130, 10], [1.0, 1.0, 1.0, 1.0]])
        # Transformation matrices for the finger width
        R_fw1 = [[np.cos(tl - np.pi / 2.0), -np.sin(tl - np.pi / 2), 0.0], [np.sin(tl - np.pi / 2), np.cos(tl - np.pi / 2), 0.0], [0.0, 0.0, 1.0]]
        R_fw2 = [[np.cos(tr - np.pi / 2), -np.sin(tr - np.pi / 2), self.wp], [np.sin(tr - np.pi / 2), np.cos(tr - np.pi / 2), 0.0], [0.0, 0.0, 1.0]]

        # finger Coordinates 1-> Left, 2-> Right
        pts_fw1 = np.dot(R_fw1, l_fw_pts)
        pts_fw2 = np.dot(R_fw2, r_fw_pts)

        # Plotting the fingers
        fw_1 = np.transpose([[pts_fw1[0, :]], [pts_fw1[1, :]]]).reshape((4, 2))
        fw_2 = np.transpose([[pts_fw2[0, :]], [pts_fw2[1, :]]]).reshape((4, 2))
        
        return fw_1*2.5, fw_2*2.5 # *2.5 for scaling up output

    def render(self):
        self._update_finger()
        self.switch_to()
        self.dispatch_events()
        self.dispatch_event('on_draw')
        self.flip()

    def on_draw(self):
        self.clear()
        self.batch.draw()
 
    def _update_finger(self):
        # Check action in ff_info['a'] and visualize based on it
        if (self.ff_info['a'][0] != 0 and self.ff_info['a'][1] == 0): # Action is sliding on left finger
            obj_pos_, obj_center = self.slide_Left_obj(self.ff_info['t'][1], self.ff_info['d'][1]) 
            finger_l_, finger_r_ = self.slide_Left_fingers(self.ff_info['t'][1], self.ff_info['d'][1])            
        elif (self.ff_info['a'][1] != 0 and self.ff_info['a'][0] == 0): # Action is sliding on right finger
            obj_pos_, obj_center = self.slide_Right_obj(self.ff_info['t'][0], self.ff_info['d'][0]) 
            finger_l_, finger_r_ = self.slide_Right_fingers(self.ff_info['t'][0], self.ff_info['d'][0]) 
        else:    
            print("ff_info['a'] : [0 0]")
            obj_pos_, obj_center = self.slide_Right_obj(self.ff_info['t'][0], self.ff_info['d'][0]) 
            finger_l_, finger_r_ = self.slide_Right_fingers(self.ff_info['t'][0], self.ff_info['d'][0])

        obj_pos_ += self.center_coord
        finger_l_ += self.center_coord
        finger_r_ += self.center_coord
        print('obj_center : ', obj_center)
        self.obj_loc = np.append(self.obj_loc, obj_center)
        # Updating obj_pos in graphics
        self.object.vertices = np.hstack([obj_pos_[1][0] + self.center_coord[0], obj_pos_[1][1],         
                                      obj_pos_[0][0] + self.center_coord[0], obj_pos_[0][1],
                                      obj_pos_[3][0] + self.center_coord[0], obj_pos_[3][1],
                                      obj_pos_[2][0] + self.center_coord[0], obj_pos_[2][1]])
        # Updating left finger in graphics
        self.finger_l.vertices = np.hstack([finger_l_[3][0] + self.center_coord[0], finger_l_[3][1],
                                                 finger_l_[2][0] + self.center_coord[0], finger_l_[2][1],
                                                 finger_l_[1][0] + self.center_coord[0], finger_l_[1][1],
                                                 finger_l_[0][0] + self.center_coord[0], finger_l_[0][1]])
        # Updating right finger in graphics
        self.finger_r.vertices = np.hstack([finger_r_[3][0] + self.center_coord[0], finger_r_[3][1],
                                                 finger_r_[2][0] + self.center_coord[0], finger_r_[2][1],
                                                 finger_r_[1][0] + self.center_coord[0], finger_r_[1][1],
                                                 finger_r_[0][0] + self.center_coord[0], finger_r_[0][1]])                                         

if __name__ == '__main__':
    env = FFEnv()
    count = 0
    while True:
        print("Action Iteration : ", count)
        env.render()
        #break
        env.step(env.sample_action())
        count += 1 
        print('-------')   
        #env.reset()    
        print('-------')
        print("get goal point : ", env.get_goal_point())
        if (count >= 1):
            break
            
        