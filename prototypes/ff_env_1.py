import numpy as np
import pyglet
import random
import time
from pyglet.window import key

class FFEnv(object):
    viewer = None
    dt = 0.1    # refresh rate
    action_bound = [-1, 1]
    goal = {'x': 100., 'y': 100.}
    state_dim = 2
    action_dim = 2

    w0 = 25  # Object width
    wp = 50  # 
    fw = 18  # Finger width

    def __init__(self):
        self.ff_info = np.zeros(2, dtype=[('d', np.float32), ('t', np.float32), ('a', np.int)])
        self.ff_info['t'][0] = np.pi/2
        self.ff_info['d'][0] = 50
        self.ff_info['a'] = 0

    def step(self, action):
        done = False
        r = 0.

        # Whichever action is given, clip it,check the limits and add the actions to that particular theta
        # if it crosses the limits then clip it and normalize it  
        if (action[0] == 0):
            # Action : Sliding on Left Finger
            # Give Right Finger Pararmeters and get Left Finger Paramters -> Call translation Left finger 
            action[1] = np.clip(action[1], *self.action_bound) # Clipping the action
            self.ff_info['t'][1] += action[1] *self.dt # Adding the action delta theta to theta_left or t_l
            if ( self.ff_info['t'][1] > 2.443 ):# greater than 140 deg
                self.ff_info['t'][1] = 2.443
            if ( self.ff_info['t'][1] < 0.69 ): # Lesser than 40 deg
                self.ff_info['t'][1] = 0.69323
            self.ff_info['t'][1] %= np.pi * 2 # normalize
            # Setting tl, dl
            self.ff_info['t'][0], self.ff_info['d'][0] = self.calc_left_config(self.ff_info['t'][1], self.ff_info['d'][1]) 
            self.ff_info['a'][1] = 1 # Action right is enable
            self.ff_info['a'][0] = 0 # Action left is disable

        elif (action[1] == 0):
            # Action : Sliding on Right Finger
            # Give Left Finger Parameters and get Right Finger Parameters -> Call translation Right Finger
            action[0] = np.clip(action[0], *self.action_bound)
            self.ff_info['t'][0] += action[0] * self.dt
            if ( self.ff_info['t'][0] > 2.443 ):# 
                self.ff_info['t'][0] = 2.443
            if (self.ff_info['t'][0] < 0.69 ):
                self.ff_info['t'][0] = 0.69
            self.ff_info['t'][0] %= np.pi * 2    # normalize
            # Setting tr, dr
            self.ff_info['t'][1], self.ff_info['d'][1] = self.calc_right_config(self.ff_info['t'][0], self.ff_info['d'][0])
            self.ff_info['a'][0] = 1 # Action left is disable
            self.ff_info['a'][1] = 0 # Action right is enable

        # state
        s = self.ff_info['t'] # As of now only consider theta in states
        # done and reward
        done = False
        r = 0. # Sparse reward
        return s, r, done
    
    def reset(self):
        self.ff_info['t'] = 2 * np.pi/2
        return self.ff_info['t']

    def render(self):
        if self.viewer is None:
            self.viewer = Viewer(self.ff_info, self.goal)
        self.viewer.render()

    def sample_action(self):
        #return np.random.rand(1)-0.5    # two radians
        action = np.zeros(2)
        action_i = np.random.rand(1)-0.5
        action_list = [0, 1]
        list_i = random.choice(action_list)
        if (list_i == 0):
            action[0] = action_i
        elif (list_i == 1):
            action[1] = action_i
        #print('--------------------action :', action)
        return action

    def calc_left_config(self, tr, dr):
        d2v = np.array([dr * np.cos(np.float64(tr)), dr * np.sin(np.float64(tr))])
        w0v = np.array([self.w0 * np.sin(np.float64(tr)), -self.w0 * np.cos(np.float64(tr))])
        wpv = np.array([self.wp, 0.])
        f1v = np.array([self.fw * np.sin(np.float64(tr)), -self.fw * np.cos(np.float64(tr))])
        av = d2v - f1v - w0v + wpv
        # Calculated Values of thetal, dl
        dl = np.sqrt(float((av * av).sum() - self.fw * self.fw))
        tl = np.arctan2(float(av[1]), float(av[0])) + np.arctan2(self.fw, dl)
        return tl, dl

    def calc_right_config(self, tl, dl):
        d1v = np.array([dl * np.cos(tl), dl * np.sin(tl)])
        w0v = np.array([self.w0 * np.sin(tl), self.w0 * np.cos(tl)])
        wpv = np.array([self.wp, 0.])
        f1v = np.array([self.fw * np.sin(tl), self.fw * np.cos(tl)])
        av = d1v + w0v + f1v - wpv
        # Calculated Values of thetar, dr
        dr = np.sqrt(float((av * av).sum() - self.fw * self.fw))
        tr = np.arctan2(float(av[1]), float(av[0])) - np.arctan2(self.fw, dr)
        return tr, dr

class Viewer(pyglet.window.Window):
    w0 = 25  # Object width
    wp = 50  # 
    fw = 18  # Finger width

    """
    tl = np.pi / 2
    tr = np.pi / 2 
    """
    dl = 62 # distance from x-axis to left bottom of the object
    dr = 50  # distance from x-axis to right bottom of the object

    def __init__(self, ff_info, goal):
        # vsync=False to not use the monitor FPS, we can speed up training
        super(Viewer, self).__init__(width=500, height=500, resizable=False, caption='FrictoinFinger', vsync=False)
        pyglet.gl.glClearColor(1, 1, 1, 1)
        self.ff_info = ff_info

        self.center_coord = np.array([200, 0]) 
        # Calling translateLeft_obj and translateLeft_fingers just to initialize the position of object and finger positions
        self.obj_pos, obj_center = self.slide_Left_obj(self.ff_info['t'][1], self.ff_info['d'][1]) + self.center_coord
        self.finger_l, self.finger_r = self.slide_Left_fingers(self.ff_info['t'][1], self.ff_info['d'][1]) + self.center_coord
        self.batch = pyglet.graphics.Batch()  # display whole batch at once

        self.object = self.batch.add(
            4, pyglet.gl.GL_QUADS, None,    # 4 corners
            ('v2f', [self.obj_pos[1][0], self.obj_pos[1][1],         # location
                     self.obj_pos[0][0], self.obj_pos[0][1],
                     self.obj_pos[3][0], self.obj_pos[3][1],
                     self.obj_pos[2][0], self.obj_pos[2][1]]),
            ('c3B', (86, 109, 249) * 4))    # color
        
        self.finger_l = self.batch.add(
            4, pyglet.gl.GL_QUADS, None,
            ('v2f', [self.finger_l[3][0], self.finger_l[3][1],
                     self.finger_l[2][0], self.finger_l[2][1],
                     self.finger_l[1][0], self.finger_l[1][1],
                     self.finger_l[0][0], self.finger_l[0][1]]),
            ('c3B', (249, 86, 86) * 4,))    # color
        self.finger_r = self.batch.add(
            4, pyglet.gl.GL_QUADS, None,
            ('v2f', [self.finger_r[3][0], self.finger_r[3][1],
                     self.finger_r[2][0], self.finger_r[2][1],
                     self.finger_r[1][0], self.finger_r[1][1],
                     self.finger_r[0][0], self.finger_r[0][1] ]),
                     ('c3B', (249, 86, 86) * 4,))
        
    def slide_Left_obj(self,tr, dr):
        # -------------------
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
        obj_center = np.vstack([x_square, y_square])
        return pts*2.5, obj_center*2.5

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
        #print("fw_1 :", fw_1)
        #print("fw_2 :", fw_2)
        return fw_1*2.5, fw_2*2.5

    def sliding_on_left_finger(self, tr, dr):
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
        obj_center = np.vstack([x_square, y_square])

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
        #print("fw_1 :", fw_1)
        #print("fw_2 :", fw_2)

        return pts*2.5, obj_center*2.5, fw_1*2.5, fw_2*2.5

    def slide_Right_obj(self,tl, dl):
        """
        Input : 
        tl : theta_left
        dl : left distance from object to origin
        Output : Left and Right Finger Position 
        """
        # Transformation Matrix
        x_square = (dl + self.w0 / 2.) * np.cos(tl) + (self.w0 / 2. + self.fw) * np.sin(tl) # x_sq (Center of the object)
        y_square = (dl + self.w0 / 2.) * np.sin(tl) - (self.w0 / 2. + self.fw) * np.cos(tl) # y_sq (Center of the object)

        pts = np.array([[-self.w0 / 2., -self.w0 / 2., self.w0 / 2., self.w0 / 2.], [-self.w0 / 2., self.w0 / 2., self.w0 / 2., -self.w0 / 2.], [1, 1, 1, 1]])
        R = np.array([[np.cos(tl), -np.sin(tl), x_square], [np.sin(tl), np.cos(tl), y_square], [0, 0, 1]])

        # Points after transformation
        pts_new = np.dot(R, pts)
        
        # Plotting the Object
        pts = np.transpose([[pts_new[0, :]], [pts_new[1, :]]])
        pts = pts.reshape((4, 2))
        obj_center = np.vstack([x_square, y_square])
        return pts*2.5, obj_center*2.5

    def slide_Right_fingers(self, tl, dl):

        # Calculate theta1, dl
        d1v = np.array([dl * np.cos(tl), dl * np.sin(tl)])
        w0v = np.array([self.w0 * np.sin(tl), self.w0 * np.cos(tl)])
        wpv = np.array([self.wp, 0.])
        f1v = np.array([self.fw * np.sin(tl), self.fw * np.cos(tl)])
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
        #print("fw_1 :", fw_1)
        #print("fw_2 :", fw_2)
        return fw_1*2.5, fw_2*2.5

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
        #print("ff_info : ", self.ff_info)
        #print('ff_info[d] : ', self.ff_info['d'])
        if (self.ff_info['a'][1] == 0):
            # Sliding on Right finger
            #print(' Actuating Right Finger')
            obj_pos_, obj_center = self.slide_Right_obj(self.ff_info['t'][0], self.ff_info['d'][0])
            finger_l_, finger_r_ = self.slide_Right_fingers(self.ff_info['t'][0], self.ff_info['d'][0])
        elif (self.ff_info['a'][0] == 0):
            # Action is of Left finger
            #print('Actuating Left Finger')
            obj_pos_, obj_center = self.slide_Left_obj(self.ff_info['t'][1], self.ff_info['d'][1])
            finger_l_, finger_r_ = self.slide_Left_fingers(self.ff_info['t'][1], self.ff_info['d'][1])

        #print("dl : ", self.ff_info['d'][0])
        #print("dr : ", self.ff_info['d'][1])
        #print("tl : ", self.ff_info['t'][0])
        #print("tr : ", self.ff_info['t'][1])
        #print("a : ", self.ff_info['a'])
        obj_pos_ += self.center_coord
        finger_l_ += self.center_coord
        finger_r_ += self.center_coord
        #print("obj_center : ", obj_center)
        #print("finger_l_ : ", finger_l_)
        #print("finger_r_ : ", finger_r_)

        self.object.vertices = np.hstack([obj_pos_[1][0], obj_pos_[1][1],         
                                      obj_pos_[0][0], obj_pos_[0][1],
                                      obj_pos_[3][0], obj_pos_[3][1],
                                      obj_pos_[2][0], obj_pos_[2][1]])
        self.finger_l.vertices = np.hstack([finger_l_[3][0], finger_l_[3][1],
                                                 finger_l_[2][0], finger_l_[2][1],
                                                 finger_l_[1][0], finger_l_[1][1],
                                                 finger_l_[0][0], finger_l_[0][1]])
        self.finger_r.vertices = np.hstack([finger_r_[3][0], finger_r_[3][1],
                                                 finger_r_[2][0], finger_r_[2][1],
                                                 finger_r_[1][0], finger_r_[1][1],
                                                 finger_r_[0][0], finger_r_[0][1]])

if __name__ == '__main__':
    env = FFEnv()
    count = 0
    #start_time = time.time()
    while True:
        env.render()
        env.step(env.sample_action())

        """
        if (count >= 3):
            break
        count += 1
        """

        """
        count += 1
        if (time.time() - start_time >= 1):
            print("count : ", count)
            break
        """