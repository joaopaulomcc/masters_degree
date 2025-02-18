import numpy as np
from numpy import sin, cos, tan, arccos, arcsin, arctan
from pyquaternion import Quaternion

from .. import mathematics as m
from numba import jit

import sys

# --------------------------------------------------------------------------------------------------


@jit(nopython=True)
def distance_point_to_line(line_point_1, line_point_2, point):
    """
    reference: http://mathworld.wolfram.com/Point-LineDistance3-Dimensional.html
    """
    x0 = point
    x1 = line_point_1
    x2 = line_point_2

    distance = m.norm(m.cross((x0 - x1), (x0 - x2))) / m.norm(x2 - x1)

    return distance


# --------------------------------------------------------------------------------------------------


@jit(nopython=True)
def distance_between_points(point_1, point_2):

    distance = (
        (point_2[0] - point_1[0]) ** 2
        + (point_2[1] - point_1[1]) ** 2
        + (point_2[2] - point_1[2]) ** 2
    ) ** 0.5

    return distance


# --------------------------------------------------------------------------------------------------


def discretization(discretization_type, n_points, control_surface_hinge_position=None):

    if discretization_type == "linear":
        chord_points = np.linspace(0, 1, n_points)

    elif discretization_type == "cos":
        angles = np.linspace(np.pi, np.pi / 2, n_points)
        chord_points = cos(angles) + 1

    elif discretization_type == "sin":
        angles = np.linspace(0, np.pi / 2, n_points)
        chord_points = sin(angles)

    elif discretization_type == "cos_sim":
        angles = np.linspace(np.pi, 0, n_points)
        chord_points = cos(angles) / 2 + 0.5

    # Change discretization in order to put panel division at control surface hinge line
    if control_surface_hinge_position is not None:
        chord_points, hinge_index = replace_closest(
            chord_points, control_surface_hinge_position
        )
    else:
        hinge_index = None

    return chord_points, hinge_index


# --------------------------------------------------------------------------------------------------


def replace_closest(array, value):

    closest_index = (np.abs(array - value)).argmin()
    new_array = array.copy()
    new_array[closest_index] = value

    return new_array, closest_index


# --------------------------------------------------------------------------------------------------


def grid_to_vector(x_grid, y_grid, z_grid):

    x_vector = np.reshape(x_grid, x_grid.size)[np.newaxis]
    y_vector = np.reshape(y_grid, y_grid.size)[np.newaxis]
    z_vector = np.reshape(z_grid, z_grid.size)[np.newaxis]

    points_vector = np.concatenate((x_vector, y_vector, z_vector), axis=0)

    return points_vector


# --------------------------------------------------------------------------------------------------


def vector_to_grid(points_vector, shape):

    x_grid = np.reshape(points_vector[0, :], shape)
    y_grid = np.reshape(points_vector[1, :], shape)
    z_grid = np.reshape(points_vector[2, :], shape)

    return x_grid, y_grid, z_grid


# --------------------------------------------------------------------------------------------------


def rotate_point(point_coord, rot_axis, rot_center, rot_angle, degrees=False):
    """Rotates a point around an axis

    Args:
        point_coord [[float, float, float]]: x, y and z coordinates of the points, every column is a point
        rot_axis [float, float, float]: vector that will be used as rotation axis
        rot_center [float, float, float]: point that will be used as rotation center
        rot_angle [float]: angle of rotation in radians (default) or degrees if degrees = True
        degrees [bool]: True if the user wants to use angles in degrees

    Returns:
        point [float, float, float]: coordinates of the rotated point
    """

    # Converts inputs to numpy arrays, normalizes axis vector
    rot_center = (rot_center[np.newaxis]).transpose()
    U = m.normalize(rot_axis)

    if degrees:
        theta = np.radians(rot_angle)
    else:
        theta = rot_angle

    u0 = U[0]
    u1 = U[1]
    u2 = U[2]

    # Calculating rotation matrix
    # reference: https://en.wikipedia.org/wiki/Rotation_matrix - "Rotation matrix from axis and angle"

    # Identity matrix
    I = np.identity(3)

    # Cross product matrix
    CPM = np.array([[0.0, -u2, u1], [u2, 0.0, -u0], [-u1, u0, 0.0]])

    # Tensor product U X U, this is NOT a cross product
    TP = np.tensordot(U, U, axes=0)

    # Rotation Matrix
    R = cos(theta) * I + sin(theta) * CPM + (1 - cos(theta)) * TP

    # Calculating rotated point

    # Translates points so rotation center is the origin of the coordinate system
    point_coord = point_coord - rot_center

    # Rotates all points
    rotated_points = R @ point_coord

    # Undo translation
    rotated_points = rotated_points + rot_center

    return rotated_points


# --------------------------------------------------------------------------------------------------


def mirror_grid(grid_xx, grid_yy, grid_zz, mirror_plane):

    if mirror_plane == "XY" or mirror_plane == "xy":

        new_grid_zz = -grid_zz

        new_grid_xx = grid_xx
        new_grid_yy = grid_yy

    elif mirror_plane == "XZ" or mirror_plane == "xz":

        new_grid_yy = np.flip(-grid_yy, axis=1)

        new_grid_xx = np.flip(grid_xx, axis=1)
        new_grid_zz = np.flip(grid_zz, axis=1)

    elif mirror_plane == "YZ" or mirror_plane == "yz":

        new_grid_xx = np.flip(-grid_xx, axis=0)

        new_grid_yy = np.flip(grid_yy, axis=0)
        new_grid_zz = np.flip(grid_zz, axis=0)

    else:
        print("ERROR: Mirror plane not recognized")
        return None

    return new_grid_xx, new_grid_yy, new_grid_zz


# --------------------------------------------------------------------------------------------------


def translate_grid(
    grid_xx, grid_yy, grid_zz, final_point, start_point=np.array([0, 0, 0])
):

    translation_vector = final_point - start_point
    x_translation = translation_vector[0]
    y_translation = translation_vector[1]
    z_translation = translation_vector[2]

    new_grid_xx = grid_xx + x_translation
    new_grid_yy = grid_yy + y_translation
    new_grid_zz = grid_zz + z_translation

    return new_grid_xx, new_grid_yy, new_grid_zz


# --------------------------------------------------------------------------------------------------


def rotate_grid(grid_xx, grid_yy, grid_zz, rot_axis, rot_center, rot_angle):

    points = grid_to_vector(grid_xx, grid_yy, grid_zz)

    rot_points = rotate_point(points, rot_axis, rot_center, rot_angle)

    shape = np.shape(grid_xx)
    new_grid_xx, new_grid_yy, new_grid_zz = vector_to_grid(rot_points, shape)

    return new_grid_xx, new_grid_yy, new_grid_zz


# --------------------------------------------------------------------------------------------------


def connect_surface_grid(
    surface_list,
    marco_surface_incidence,
    macro_surface_position,
    n_chord_panels,
    n_span_panels_list,
    chord_discretization,
    span_discretization_list,
    torsion_function_list,
    torsion_center,
    control_surface_dictionary,
):

    connected_grids = []

    for i, surface in enumerate(surface_list):

        n_span_panels = n_span_panels_list[i]
        span_discretization = span_discretization_list[i]
        torsion_function = torsion_function_list[i]

        if surface.identifier in control_surface_dictionary:
            control_surface_deflection = control_surface_dictionary[surface.identifier]
        else:
            control_surface_deflection = 0

        apply_torsion = False

        # Generates surface mesh, with torsion and dihedral
        surface_mesh_xx, surface_mesh_yy, surface_mesh_zz = surface.generate_aero_mesh(
            n_span_panels,
            n_chord_panels,
            control_surface_deflection,
            chord_discretization,
            span_discretization,
            apply_torsion,
            torsion_function,
            torsion_center,
        )

        # When the surface is not at the root
        if i != 0:

            last_surface = connected_grids[i - 1]
            shape = np.shape(last_surface["xx"])

            # Get tip line segment from last surface
            tip_xx = last_surface["xx"][:, shape[1] - 1]
            tip_yy = last_surface["yy"][:, shape[1] - 1]
            tip_zz = last_surface["zz"][:, shape[1] - 1]

            tip_lead_edge = np.array([tip_xx[0], tip_yy[0], tip_zz[0]])
            tip_trai_edge = np.array([tip_xx[1], tip_yy[1], tip_zz[1]])

            tip_vector = tip_trai_edge - tip_lead_edge

            # Translate surface so it's root leading edge contacts the tip leading edge of the last
            # surface
            final_point = tip_lead_edge
            surface_mesh_xx, surface_mesh_yy, surface_mesh_zz = translate_grid(
                surface_mesh_xx, surface_mesh_yy, surface_mesh_zz, final_point
            )

            # Get root line segment from current surface
            root_xx = surface_mesh_xx[:, 0]
            root_yy = surface_mesh_yy[:, 0]
            root_zz = surface_mesh_zz[:, 0]

            root_lead_edge = np.array([root_xx[0], root_yy[0], root_zz[0]])
            root_trai_edge = np.array([root_xx[1], root_yy[1], root_zz[1]])

            root_vector = root_trai_edge - root_lead_edge

            # use cross vector to find rot axis
            rot_axis = m.cross(root_vector, tip_vector)

            # find by wich angle the surcafe needs to be rotates
            rot_angle = angle_between(root_vector, tip_vector)

            # Rotates surface around tip_lead_edge so tip_vector and root_vector match
            rot_center = tip_lead_edge

            surface_mesh_xx, surface_mesh_yy, surface_mesh_zz = rotate_grid(
                surface_mesh_xx,
                surface_mesh_yy,
                surface_mesh_zz,
                rot_axis,
                rot_center,
                rot_angle,
            )

        else:
            # Translates grid to correct position
            final_point = macro_surface_position
            surface_mesh_xx, surface_mesh_yy, surface_mesh_zz = translate_grid(
                surface_mesh_xx, surface_mesh_yy, surface_mesh_zz, final_point
            )

            # Apply macro surface incidence angle, other surfaces will automatically have this incidence
            rot_axis = np.array([0, 1, 0])  # Y axis
            rot_center = macro_surface_position
            rot_angle = marco_surface_incidence
            surface_mesh_xx, surface_mesh_yy, surface_mesh_zz = rotate_grid(
                surface_mesh_xx,
                surface_mesh_yy,
                surface_mesh_zz,
                rot_axis,
                rot_center,
                rot_angle,
            )

        connected_grids.append(
            {"xx": surface_mesh_xx, "yy": surface_mesh_yy, "zz": surface_mesh_zz}
        )

    return connected_grids


# --------------------------------------------------------------------------------------------------


def connect_surface_nodes(
    surface_list,
    n_elements_list,
    position,
    incidence_angle,
    torsion_center,
    mirror=False,
):

    connected_nodes = []

    for i, surface in enumerate(surface_list):

        n_elements = n_elements_list[i]
        n_nodes = n_elements + 1

        # Generates surface mesh, with torsion and dihedral
        surface_nodes = surface.generate_structure_nodes(
            n_nodes, torsion_center, mirror
        )

        # When the surface is not at the root
        if i != 0:

            last_surface_nodes = connected_nodes[i - 1]
            tip_node = last_surface_nodes[len(last_surface_nodes) - 1]

            # Translate nodes so it's root leading edge contacts the tip leading edge of the last surface
            translation_vector = tip_node.xyz - surface_nodes[0].xyz

            for j, node in enumerate(surface_nodes):

                surface_nodes[j] = node.translate(translation_vector)

            # use cross vector to find rot axis between tip node and root node z axis
            rot_axis = m.cross(surface_nodes[0].z_axis, tip_node.z_axis)

            # find by wich angle the nodes needs to be rotates
            rot_angle = angle_between(surface_nodes[0].z_axis, tip_node.z_axis)

            # Rotates surface around tip_lead_edge so tip z vector and root z vector match

            rot_center = tip_node.xyz
            rot_quaternion = Quaternion(axis=rot_axis, angle=rot_angle)

            for j, node in enumerate(surface_nodes):

                surface_nodes[j] = node.rotate(rot_quaternion, rot_center)

        else:
            # Translates grid to correct position
            final_point = position

            for j, node in enumerate(surface_nodes):

                surface_nodes[j] = node.translate(position)

            # Apply macro surface incidence angle, other surfaces will automatically have this incidence
            rot_axis = np.array([0, 1, 0])  # Y axis
            rot_center = position
            rot_angle = incidence_angle
            rot_quaternion = Quaternion(axis=rot_axis, angle=rot_angle)

            for j, node in enumerate(surface_nodes):
                surface_nodes[j] = node.rotate(rot_quaternion, rot_center)

        connected_nodes.append(surface_nodes)

    return connected_nodes


# --------------------------------------------------------------------------------------------------


def velocity_field_function_generator(
    velocity_vector, rotation_vector, attitude_vector, center
):

    # This is a horrible hack

    v_x = velocity_vector[0]
    v_y = velocity_vector[0]
    v_z = velocity_vector[0]

    r_x = rotation_vector[0]
    r_y = rotation_vector[1]
    r_z = rotation_vector[2]

    alpha = attitude_vector[0]
    beta = attitude_vector[1]
    gamma = attitude_vector[2]

    x_axis = np.array([1.0, 0.0, 0.0])
    y_axis = np.array([0.0, 1.0, 0.0])
    z_axis = np.array([0.0, 0.0, 1.0])
    origin = np.array([0.0, 0.0, 0.0])

    true_airspeed = velocity_vector[0]

    cg_velocity = np.array([true_airspeed, 0, 0])[np.newaxis].transpose()

    # Rotate around y for alfa
    cg_velocity = rotate_point(cg_velocity, y_axis, origin, -alpha, degrees=True)

    # Rotate around z for beta
    cg_velocity = rotate_point(cg_velocity, z_axis, origin, -beta, degrees=True)

    # Rotate around x for gamma
    cg_velocity = rotate_point(cg_velocity, x_axis, origin, -gamma, degrees=True)

    cg_velocity = cg_velocity.transpose()[0]

    def velocity_field_function(point_location):

        r = point_location - center
        tangential_velocity = -m.cross(rotation_vector, r)

        flow_velocity = cg_velocity + tangential_velocity

        return flow_velocity

    return velocity_field_function


# --------------------------------------------------------------------------------------------------


def angle_between(vector_1, vector_2):

    cos_theta = m.dot(vector_1, vector_2) / (m.norm(vector_1) * m.norm(vector_2))
    theta = np.arccos(cos_theta)

    return theta


# --------------------------------------------------------------------------------------------------


def cos_between(vector_1, vector_2):

    cos_theta = m.dot(vector_1, vector_2) / (m.norm(vector_1) * m.norm(vector_2))

    return cos_theta


# --------------------------------------------------------------------------------------------------


def interpolate_nodes(node_1, node_2, n_nodes):

    node_list = []

    for i, quaternion in enumerate(
        Quaternion.intermediates(
            node_1.quaternion, node_2.quaternion, (n_nodes - 2), include_endpoints=True
        )
    ):

        vector = node_2.xyz - node_1.xyz

        node_xyz = node_1.xyz + i * vector / (n_nodes - 1)
        node_quaternion = quaternion

        node_list.append([node_xyz, node_quaternion])

    return node_list


# --------------------------------------------------------------------------------------------------


def change_coord_sys(vector, X, Y, Z):

    base_matrix = np.array([[X[0], Y[0], Z[0]], [X[1], Y[1], Z[1]], [X[2], Y[2], Z[2]]])

    transformation_matrix = np.linalg.inv(base_matrix)

    new_vector = transformation_matrix @ vector

    return new_vector


# --------------------------------------------------------------------------------------------------


def decompose_rotation(rotation_axis, rotation_angle, axis_1, axis_2, axis_3):

    transformed_rotation_axis = change_coord_sys(rotation_axis, axis_1, axis_2, axis_3)

    rotation_quaternion = Quaternion(
        axis=transformed_rotation_axis, angle=rotation_angle
    )

    yaw_pitch_roll = rotation_quaternion.yaw_pitch_roll

    return yaw_pitch_roll


# --------------------------------------------------------------------------------------------------


def apply_torsion_to_grid(grid_dict, torsion_center, torsion_function, surface):

    xx = grid_dict["xx"]
    yy = grid_dict["yy"]
    zz = grid_dict["zz"]

    n_span_points = len(xx[0, :])
    n_chord_points = len(xx[:, 0])

    grid_points_xx = np.zeros(np.shape(xx))
    grid_points_yy = np.zeros(np.shape(yy))
    grid_points_zz = np.zeros(np.shape(zz))

    for i in range(n_span_points):
        # Extract section points from grid
        section_points_x = xx[:, i]
        section_points_y = yy[:, i]
        section_points_z = zz[:, i]

        # Convert points from grid to list
        section_points = grid_to_vector(
            section_points_x, section_points_y, section_points_z
        )

        # Calculate rotation characteristics and apply rotation
        span_position = abs(section_points_y[0]) / (
            surface.length * np.cos(surface.dihedral_angle_rad)
        )
        rot_angle = torsion_function(span_position)
        rot_axis = np.array([0, 1, 0])  # Y axis

        # Calculate Rotation center
        section_point_1 = section_points[:, 0]
        section_point_2 = section_points[:, 1]
        local_chord = surface.root_chord + span_position * (
            surface.tip_chord - surface.root_chord
        )

        section_vector = m.normalize(section_point_2 - section_point_1)
        rot_center = section_point_1 + torsion_center * section_vector * local_chord

        rot_section_points = rotate_point(
            section_points, rot_axis, rot_center, rot_angle
        )

        # Convert section points from list to grid
        shape = (n_chord_points, 1)
        rot_section_points_x, rot_section_points_y, rot_section_points_z = vector_to_grid(
            rot_section_points, shape
        )

        # Paste rotated section into grid
        grid_points_xx[:, i] = rot_section_points_x[:, 0]
        grid_points_yy[:, i] = rot_section_points_y[:, 0]
        grid_points_zz[:, i] = rot_section_points_z[:, 0]

    return {"xx": grid_points_xx, "yy": grid_points_yy, "zz": grid_points_zz}


# --------------------------------------------------------------------------------------------------


def apply_torsion_to_nodes(nodes_list, torsion_center, torsion_function, surface):

    n_span_points = len(nodes_list)

    rot_nodes_prop_list = []

    for i, node in enumerate(nodes_list):

        # Calculate wing properties at node location
        span_position = abs(node.xyz[1]) / (
            surface.length * np.cos(surface.dihedral_angle_rad)
        )

        local_chord = surface.root_chord + span_position * (
            surface.tip_chord - surface.root_chord
        )

        # Calculate position of the torsion center and rotation properties
        leading_edge_x = (
            span_position * surface.length * tan(surface.leading_edge_sweep_angle_rad)
        )
        leading_edge_y = span_position * surface.span
        leading_edge_z = span_position * surface.span * tan(surface.dihedral_angle_rad)

        rot_angle = torsion_function(span_position)
        rot_axis = np.array([0, 1, 0])  # Y axis
        rot_center = np.array(
            [
                leading_edge_x + local_chord * torsion_center,
                leading_edge_y,
                leading_edge_z,
            ]
        )
        rot_quaternion = Quaternion(axis=rot_axis, angle=rot_angle)

        # Rotate Node around torsion center

        node_location = node.rotate(
            rotation_quaternion=rot_quaternion, rotation_center=rot_center
        )

        yaw_pitch_row = decompose_rotation(
            rot_axis, rot_angle, node.x_axis, node.y_axis, node.z_axis
        )

        rot_quaternion = Quaternion(axis=node.x_axis, angle=yaw_pitch_row[2])
        rot_center = node.xyz

        node_rotation = node.rotate(
            rotation_quaternion=rot_quaternion, rotation_center=rot_center
        )

        rot_node_prop = [node_location.xyz, node_rotation.quaternion]

        rot_nodes_prop_list.append(rot_node_prop)

    return rot_nodes_prop_list


# --------------------------------------------------------------------------------------------------


def create_structure_node_vector(structure_struct_grid):

    node_vector = []


    # Add all nodes to a vector and sort then by node number and remove duplicates

    for component_grid in structure_struct_grid:
        node_vector += component_grid

    # Sort the vector
    node_vector.sort(key=lambda x: x.number)

    last_node_number = None
    remove_queue = []

    # Find nodes with the same node number
    for i, node in enumerate(node_vector):

        if node.number == last_node_number:
            remove_queue.append(i)
        else:
            last_node_number = node.number

    # Delete duplicate nodes
    # Iterate backwards so indice number don't change
    for i in reversed(remove_queue):
        del node_vector[i]

    return node_vector

# --------------------------------------------------------------------------------------------------


def macrosurface_aero_grid_to_single_grid(macro_surface_mesh):

    n_span_points = 0
    n_chord_points = 0

    # Count number of chord and spam points
    for surface_mesh in macro_surface_mesh:
        i, j = np.shape(surface_mesh["xx"])
        n_chord_points = i
        n_span_points += j

    # Initialize single grid
    single_grid_xx = np.zeros((n_chord_points, n_span_points))
    single_grid_yy = np.zeros((n_chord_points, n_span_points))
    single_grid_zz = np.zeros((n_chord_points, n_span_points))

    # Populate Single Grid
    span_index = 0
    for surface_mesh in macro_surface_mesh:
        n_x, n_y = np.shape(surface_mesh["xx"])

        for i in range(n_x):
            for j in range(n_y):
                single_grid_xx[i][j + span_index] = surface_mesh["xx"][i, j]
                single_grid_yy[i][j + span_index] = surface_mesh["yy"][i, j]
                single_grid_zz[i][j + span_index] = surface_mesh["zz"][i, j]

        span_index += n_y

    single_grid = {"xx":single_grid_xx, "yy":single_grid_yy, "zz":single_grid_zz}

    return single_grid

# --------------------------------------------------------------------------------------------------
