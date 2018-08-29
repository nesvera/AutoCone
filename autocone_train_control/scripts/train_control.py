#!/usr/bin/env python
import rospy
import rospkg

from gazebo_msgs.srv import (
    SpawnModel, 
    GetWorldProperties, 
    DeleteModel,
)

#from gazebo_msgs.msg import *

from std_msgs.msg import String
from std_srvs.srv import Empty

from geometry_msgs.msg import Pose

import math

class TrainControl:

    def __init__(self):
        
        # Path to the models
        self.cone_model_path = rospkg.RosPack().get_path('autocone_description') + "/urdf/models/mini_cone/model.sdf"
        self.cone_file = None

        # Open and store models to spawn
        try:
            f = open(self.cone_model_path, 'r')
            self.cone_file = f.read()

        except:
            print("Could not read file: " + self.cone_model_path)

        # Models identifiers
        self.cone_count = 0

    def spawn_cone(self, posX, posY):
        
        try:
            spawn = rospy.ServiceProxy("gazebo/spawn_sdf_model", SpawnModel)
            rospy.wait_for_service("gazebo/spawn_sdf_model")
            
            cone_pose = Pose()
            cone_pose.position.x = posX
            cone_pose.position.y = posY
            cone_pose.position.z = 0

            model_name = "cone_" + str(self.cone_count)
            spawn(model_name, self.cone_file, "default", cone_pose, "world")
            
            self.cone_count += 1

        except rospy.ServiceException, e:
            print("Error: " + e)

    def reset_world(self):

        # Service to return models spawned on gazebo world
        world_properties = rospy.ServiceProxy("gazebo/get_world_properties", GetWorldProperties)
        rospy.wait_for_service("gazebo/get_world_properties")
        
        model_names = None

        # Read models
        try:
            resp_properties = world_properties()
            model_names = resp_properties.model_names

        except rospy.ServiceException, e:
            print("Error: " + e)

        
        delete_model = rospy.ServiceProxy('/gazebo/delete_model', DeleteModel)

        # Remove cones and car
        try:
            for name in model_names:

                # Dont remove ground_plane
                if "ground_plane" in name:
                    print("achou")
                    continue

                # Call delete
                resp_delete = delete_model(name)
                
                if resp_delete.success == False:
                    print("Error trying to delete cone")

        except rospy.ServiceException, e:
            print("Error: " + e)


if __name__ == '__main__':

    rospy.init_node('train_control', anonymous=True)

    b = TrainControl()

    a = 1
    x = 0
    y = 0
    theta = 0

    for i in range(4):
        a += 0.01
        theta += 0.1
        x = a*math.cos(theta)
        y = a*math.sin(theta)

        b.spawn_cone(x, y)

    raw_input()

    b.reset_world()
