############################## Imports   ######################################
#region
from config import *
#endregion
############################## helper functions ###############################
#region

def reuse_id(
    deleted_ids: np.ndarray, deleted_count: int) -> int:
    """
        Returns the id of a previously deleted object, if it exists.
        Returns -1 otherwise.
    """

    if deleted_count == 0:
        return -1
    
    return deleted_ids[deleted_count - 1]

def add_at(array: np.ndarray, i: int, entry: np.ndarray, stride: int, size: int) -> tuple[int, np.ndarray]:
    """
        Attempts to add to an array at the given position, resizing if necessary.

        Parameters:

            array: the array to add to

            i: the position to add at

            entry: the entry to add at position i

            stride: the stride of the array (numbers per element)

            size: the size of the array (number of elements)
        
        Returns:

            The new size of the array and the newly allocated array 
            (adding may necessitate a reallocation)
    """

    if i >= size:

        #reallocate!
        new_size = max(max(2 * size, i), 1)
        new_array = np.zeros(new_size * stride, dtype = array.dtype)

        for j in range(size * stride):
            new_array[j] = array[j]
        
        array = new_array
        size = new_size
    
    index = i * stride
    for j in range(stride):
        array[index + j] = entry[j]
    
    return (size, array)

def find_id(array: np.ndarray, _id: int, _max: int) -> int:
    """
        Search the given array for the target id, up to max,
        return the position of _id
    """

    for i in range(_max):
        if array[i] == _id:
            return i
    
    return -1

def overwrite(array: np.ndarray, i: int, j: int, stride: int) -> None:
    """
        Overwrite entry i in the given array with entry j.

        Parameters:

            array: the array to work with

            i: the position to overwrite

            j: the position to copy over

            stride: the stride of the array (numbers per element)
    """
    
    index_a = i * stride
    index_b = j * stride
    for k in range(stride):
        array[index_a + k] = array[index_b + k]

@njit(cache = True)
def update_positions(
    instance_types: np.ndarray,
    positions: tuple[np.ndarray], 
    transforms: tuple[np.ndarray],
    light_data: np.ndarray, 
    count: int) -> None:
    """
        Write the transform matrices to the given array.
    """

    cubes_written = 0
    lights_written = 0
    for i in range(count):

        _id = positions[0][i]
        _type = instance_types[_id]
        write_index = lights_written
        if _type == 0:
            write_index = cubes_written

        #unpack position data
        index = 3 * i
        read_array = positions[1]
        x    = read_array[index]
        y    = read_array[index + 1]
        z    = read_array[index + 2]

        #write transforms
        if (has_components[_type] & 1):
            index = 16 * write_index
            target_array = transforms[_type]

            target_array[index]      = 1.0
            target_array[index + 5]  = 1.0
            target_array[index + 10] = 1.0
            target_array[index + 12] = x
            target_array[index + 13] = y
            target_array[index + 14] = z
            target_array[index + 15] = 1.0

        #write light position
        if (has_components[_type] & (1 << 2)):

            index = 8 * write_index
            target_array = light_data

            target_array[index]     = x
            target_array[index + 1] = y
            target_array[index + 2] = z

        if _type == 0:
            cubes_written += 1
        else:
            lights_written += 1

@njit(cache = True)
def update_eulers(
    eulers: np.ndarray, transforms: np.ndarray, 
    count: int, rate: float) -> None:
    """
        Update all those cubes! Also, write the transform matrices to the given array.
    """

    for i in range(count):

        #unpack cube data
        index = 6 * i
        e_x  = eulers[index]
        e_y  = eulers[index + 1]
        e_z  = eulers[index + 2]
        ev_x = eulers[index + 3]
        ev_y = eulers[index + 4]
        ev_z = eulers[index + 5]

        #update cube data
        e_x = (e_x + rate * ev_x) % 360
        e_y = (e_y + rate * ev_y) % 360
        e_z = (e_z + rate * ev_z) % 360

        #write transforms
        index = 16 * i

        r_y = np.radians(e_y)
        r_z = np.radians(e_z)
        c_y = np.cos(r_y)
        s_y = np.sin(r_y)
        c_z = np.cos(r_z)
        s_z = np.sin(r_z)

        transforms[index]      = c_y * c_z
        transforms[index + 1]  = c_y * s_z
        transforms[index + 2]  = -s_y
        transforms[index + 4]  = -s_z
        transforms[index + 5]  = c_z
        transforms[index + 8]  = s_y * c_z
        transforms[index + 9]  = s_y * s_z
        transforms[index + 10] = c_y

        #write euler data back
        index = 6 * i
        eulers[index]     = e_x
        eulers[index + 1] = e_y
        eulers[index + 2] = e_z

@njit(cache = True)
def update_lights(
    lights: tuple[np.ndarray],
    light_data:np.ndarray, count: int) -> None:
    """
        Write the light data to the given array.
        Lights don't have much updating to do.
    """

    for i in range(count):

        #unpack light color and strength
        index = 4 * i
        r     = lights[1][index]
        g     = lights[1][index + 1]
        b     = lights[1][index + 2]
        s     = lights[1][index + 3]

        #write light data
        index = 8 * i

        light_data[index + 4] = r
        light_data[index + 5] = g
        light_data[index + 6] = b
        light_data[index + 7] = s

@njit(cache = True)
def move_player(player: np.ndarray, d_pos: np.ndarray) -> None:
    """
        Move by the given amount in the (forwards, right, up) vectors.
    """

    x = player[0]
    y = player[1]
    z = player[2]

    for i in range(3):

        x += d_pos[i] * player[6 + 3 * i]
        y += d_pos[i] * player[7 + 3 * i]
        z += d_pos[i] * player[8 + 3 * i]

    player[0] = x
    player[1] = y
    player[2] = z

@njit(cache = True)
def spin_player(player: np.ndarray, d_eulers: np.ndarray) -> None:
    """
        Spin the camera by the given amount about the (x, y, z) axes.
    """

    e_x = player[3] + d_eulers[0]
    e_y = player[4] + d_eulers[1]
    e_z = player[5] + d_eulers[2]


    player[3] = e_x % 360
    player[4] = min(89, max(-89, e_y))
    player[5] = e_z % 360

@njit(cache = True)
def update_player(player: tuple[np.ndarray]) -> None:
    """
        Update the camera, write its view transform also.
    """

    target_array = player[0]
    e_y = target_array[4]
    e_z = target_array[5]

    c_y = np.cos(np.radians(e_y))
    s_y = np.sin(np.radians(e_y))
    c_z = np.cos(np.radians(e_z))
    s_z = np.sin(np.radians(e_z))

    f_x = c_z * c_y
    f_y = s_z * c_y
    f_z = s_y
    norm = np.sqrt(f_x * f_x + f_y * f_y + f_z * f_z)
    f_x = f_x / norm
    f_y = f_y / norm
    f_z = f_z / norm

    r_x = f_y
    r_y = -f_x
    r_z = 0.0
    norm = np.sqrt(r_x * r_x + r_y * r_y + r_z * r_z)
    r_x = r_x / norm
    r_y = r_y / norm
    r_z = r_z / norm

    u_x = r_y * f_z - r_z * f_y
    u_y = r_z * f_x - r_x * f_z
    u_z = r_x * f_y - r_y * f_x
    norm = np.sqrt(u_x * u_x + u_y * u_y + u_z * u_z)
    u_x = u_x / norm
    u_y = u_y / norm
    u_z = u_z / norm

    target_array[6] = f_x
    target_array[7] = f_y
    target_array[8] = f_z
    target_array[9] = r_x
    target_array[10] = r_y
    target_array[11] = r_z
    target_array[12] = u_x
    target_array[13] = u_y
    target_array[14] = u_z

    x = target_array[0]
    y = target_array[1]
    z = target_array[2]

    target_array = player[1]
    target_array[0] = r_x
    target_array[1] = u_x
    target_array[2] = -f_x
    target_array[4] = r_y
    target_array[5] = u_y
    target_array[6] = -f_y
    target_array[8] = r_z
    target_array[9] = u_z
    target_array[10] = -f_z
    target_array[12] = -(r_x * x + r_y * y + r_z * z)
    target_array[13] = -(u_x * x + u_y * y + u_z * z)
    target_array[14] = f_x * x + f_y * y + f_z * z
    target_array[15] = 1.0
#endregion
############################### Data Schema ###################################
#region
#---- Internal ----#
"""
    instance types:

    id(implicit): int
    obj_type: int
"""
"""
    deleted ids:
    id(implicit): int
"""
has_components: np.ndarray = np.array((3,5), dtype = np.uint8)
#CUBE: transform: true, eulers: true, light: false
#LIGHT: transform: true, eulers: false, light: true
"""
    positions:

    id: int
    pos: vec3
"""
"""
    eulers:

    id: int
    eulers: vec3
    euler_velocity: vec3
"""
"""
    lights

    id: int
    color: vec3
    strength: float
"""
#---- Hybrid ----#
"""
    Camera:
    position: 3
    eulers: 3
    forwards: 3
    right: 3
    up: 3

    stride: 15
"""
#---- Output ----#
"""
    Transform:

    stride: 16
"""
"""
    Light Data:
    pos, color, strength

    stride: 7
"""
"""
    View:

    stride: 16
"""
#endregion
##################################### Model ###################################
#region
class Scene:
    """
        Manages all objects and coordinates their interactions.
    """
    __slots__ = (
        "entity_counts",
        "instance_types", "instance_count", "instance_size",
        "deleted_ids", "deleted_count", "deleted_size",
        "positions", "position_count", "position_size",
        "eulers", "euler_count", "euler_size",
        "lights", "light_count", "light_size",
        "player", 
        "model_transforms", "model_count", "model_size",
        "light_data", "light_data_count", "light_data_size")


    def __init__(self):
        """
            Initialize the scene.
        """

        self.entity_counts: dict[int, int] = {
            ENTITY_TYPE["CUBE"]: 0,
            ENTITY_TYPE["POINTLIGHT"]: 0
        }

        self._make_internal_objects()

        #Hybrid Data
        self.player: list[np.ndarray] = [
            np.zeros(15, dtype = np.float32),
            np.zeros(16, dtype = np.float32)
        ]
        self._make_player()

        self._make_output_data()
    
    def _make_internal_objects(self) -> None:

        self.instance_types: np.ndarray = np.array([], dtype=np.uint8)
        self.instance_count = 0
        self.instance_size = 0

        self.deleted_ids: np.array = np.array([], dtype = np.uint16)
        self.deleted_count = 0
        self.deleted_size = 0

        self.positions: list[np.ndarray] = [
            np.array([], dtype=np.uint16),
            np.array([], dtype=np.float32)
        ]
        self.position_count = 0
        self.position_size = 0

        self.eulers: list[np.ndarray] = [
            np.array([], dtype=np.uint16),
            np.array([], dtype=np.float32),
        ]
        self.euler_count = 0
        self.euler_size = 0

        self.lights: list[np.array] = [
            np.array([], dtype=np.uint16),
            np.array([], dtype=np.float32),
        ]
        self.light_count = 0
        self.light_size = 0

    def make_cube(self) -> None:
        """
            Make the cube!
        """

        print(self.deleted_ids)
        print(self.deleted_count)
        _id = reuse_id(self.deleted_ids, self.deleted_count)
        if _id >= 0:
            self.deleted_count -= 1
        else:
            _id = self.instance_count
            self.instance_count += 1
        print(f"Cube will be made with id: {_id}")

        #Register id
        self.instance_size, self.instance_types = add_at(
            array = self.instance_types, i = _id, 
            entry = np.zeros(1, dtype=np.uint8), 
            stride = 1, size = self.instance_size)
        _, self.positions[0] = add_at(
            array = self.positions[0], i = self.position_count, 
            entry = np.array((_id,), dtype=np.uint16), 
            stride = 1, size = self.position_size)
        _, self.eulers[0] = add_at(
            array = self.eulers[0], i = self.euler_count, 
            entry = np.array((_id,), dtype=np.uint16), 
            stride = 1, size = self.euler_size)

        #Add position
        x = np.random.uniform(low = -10, high = 10)
        y = np.random.uniform(low = -10, high = 10)
        z = np.random.uniform(low = -10, high = 10)
        self.position_size, self.positions[1] = add_at(
            array = self.positions[1], i = self.position_count, 
            entry = np.array((x,y,z), dtype=np.float32), 
            stride = 3, size = self.position_size)
        self.position_count += 1

        #add eulers
        e_x = np.random.uniform(low = 0, high = 360)
        e_y = np.random.uniform(low = 0, high = 360)
        e_z = np.random.uniform(low = 0, high = 360)
        ev_x = np.random.uniform(low = -0.2, high = 0.2)
        ev_y = np.random.uniform(low = -0.2, high = 0.2)
        ev_z = np.random.uniform(low = -0.2, high = 0.2)
        self.euler_size, self.eulers[1] = add_at(
            array = self.eulers[1], i = self.euler_count, 
            entry = np.array(
                (e_x, e_y, e_z, ev_x, ev_y, ev_z), dtype=np.float32), 
            stride = 6, size = self.euler_size)
        self.euler_count += 1

        #add model transform
        model_transform = np.zeros(16, dtype=np.float32)
        model_transform[0] = 1.0
        model_transform[5] = 1.0
        model_transform[10] = 1.0
        model_transform[15] = 1.0
        self.model_size[0], self.model_transforms[0] = add_at(
            array = self.model_transforms[0], i = self.model_count[0],
            entry = model_transform, stride = 16,
            size = self.model_size[0]
        )
        self.model_count[0] += 1
        
        self.entity_counts[ENTITY_TYPE["CUBE"]] += 1
    
    def delete_cube(self) -> None:
        """
            Delete a cube!
        """

        #choose a random cube
        _id = 0
        while True:
            _id = np.random.randint(
                low = 0, 
                high = self.instance_count)
            if self.instance_types[_id] == 0:
                break
        
        print(f"Cube {_id} will be deleted.")
        
        #add id to garbage bin
        self.deleted_size, self.deleted_ids = add_at(
            array = self.deleted_ids, i = self.deleted_count, 
            entry = np.array((_id,), dtype = np.uint16), stride = 1,
            size = self.deleted_size
        )
        self.deleted_count += 1

        #Remove from positions
        i = find_id(
            array = self.positions[0], _id = _id, _max = self.position_count)
        self.position_count -= 1
        overwrite(self.positions[0], i, self.position_count, 1)
        overwrite(self.positions[1], i, self.position_count, 3)

        #Remove from eulers
        i = find_id(
            array = self.eulers[0], _id = _id, _max = self.euler_count)
        self.euler_count -= 1
        overwrite(self.eulers[0], i, self.euler_count, 1)
        overwrite(self.eulers[1], i, self.euler_count, 6)

        #Remove from model transform
        self.model_count[0] -= 1
        
        self.entity_counts[ENTITY_TYPE["CUBE"]] -= 1

    def make_light(self) -> None:
        """
            Make a light!
        """

        print(self.deleted_ids)
        print(self.deleted_count)
        _id = reuse_id(self.deleted_ids, self.deleted_count)
        if _id >= 0:
            self.deleted_count -= 1
        else:
            _id = self.instance_count
            self.instance_count += 1
        print(f"Light will be made with id: {_id}")

        #Register id
        self.instance_size, self.instance_types = add_at(
            array = self.instance_types, i = _id, 
            entry = np.ones(1, dtype=np.uint8), 
            stride = 1, size = self.instance_size)
        _, self.positions[0] = add_at(
            array = self.positions[0], i = self.position_count, 
            entry = np.array((_id,), dtype=np.uint16), 
            stride = 1, size = self.position_size)
        _, self.lights[0] = add_at(
            array = self.lights[0], i = self.light_count, 
            entry = np.array((_id,), dtype=np.uint16), 
            stride = 1, size = self.light_size)

        #Add position
        x = np.random.uniform(low = -10, high = 10)
        y = np.random.uniform(low = -10, high = 10)
        z = np.random.uniform(low = -10, high = 10)
        self.position_size, self.positions[1] = add_at(
            array = self.positions[1], i = self.position_count, 
            entry = np.array((x,y,z), dtype=np.float32), 
            stride = 3, size = self.position_size)
        self.position_count += 1

        #add light
        r = np.random.uniform(low = 0.5, high = 1.0)
        g = np.random.uniform(low = 0.5, high = 1.0)
        b = np.random.uniform(low = 0.5, high = 1.0)
        s = np.random.uniform(low = 2, high = 5)
        self.light_size, self.lights[1] = add_at(
            array = self.lights[1], i = self.light_count, 
            entry = np.array((r, g, b, s), dtype=np.float32), 
            stride = 4, size = self.light_size)
        self.light_count += 1

        #add model transform
        model_transform = np.zeros(16, dtype=np.float32)
        model_transform[0] = 1.0
        model_transform[5] = 1.0
        model_transform[10] = 1.0
        model_transform[15] = 1.0
        self.model_size[1], self.model_transforms[1] = add_at(
            array = self.model_transforms[1], i = self.model_count[1],
            entry = model_transform, stride = 16,
            size = self.model_size[1]
        )
        self.model_count[1] += 1

        #add light data
        light_entry = np.zeros(8, dtype=np.float32)
        self.light_data_size, self.light_data = add_at(
            array = self.light_data, i = self.light_data_count,
            entry = light_entry, stride = 8,
            size = self.light_data_size
        )
        self.light_data_count += 1
        
        self.entity_counts[ENTITY_TYPE["POINTLIGHT"]] += 1
    
    def delete_light(self) -> None:
        """
            delete a light!
        """

        #choose a random light
        _id = 0
        while True:
            _id = np.random.randint(
                low = 0, 
                high = self.instance_count)
            if self.instance_types[_id] == 1:
                break
        
        print(f"Light {_id} will be deleted.")
        
        #add id to garbage bin
        self.deleted_size, self.deleted_ids = add_at(
            array = self.deleted_ids, i = self.deleted_count, 
            entry = np.array((_id,), dtype = np.uint16), stride = 1,
            size = self.deleted_size
        )
        self.deleted_count += 1

        #Remove from positions
        i = find_id(
            array = self.positions[0], _id = _id, _max = self.position_count)
        self.position_count -= 1
        overwrite(self.positions[0], i, self.position_count, 1)
        overwrite(self.positions[1], i, self.position_count, 3)

        #Remove from lights
        i = find_id(
            array = self.lights[0], _id = _id, _max = self.light_count)
        self.light_count -= 1
        overwrite(self.lights[0], i, self.light_count, 1)
        overwrite(self.lights[1], i, self.light_count, 4)

        #Remove from model transform
        self.model_count[0] -= 1

        #Remove from light data
        self.light_data_count -= 1
        
        self.entity_counts[ENTITY_TYPE["POINTLIGHT"]] -= 1
    
    def _make_player(self) -> None:
        """
            Make the player.
        """

        x = -10
        f_x = 1.0
        r_y = -1.0
        u_z = 1.0
        #all other fields happen to be zero.

        target_array = self.player[0]
        target_array[0] = x
        target_array[6] = f_x
        target_array[10] = r_y
        target_array[14] = u_z
        
        #load identity into view transform
        target_array = self.player[1]
        for i in range(4):
            target_array[5 * i] = 1.0

    def _make_output_data(self) -> None:

        self.model_transforms: list[np.ndarray] = [
            np.array([], dtype=np.float32),
            np.array([], dtype=np.float32),
        ]
        self.model_size = [0,0]
        self.model_count = [0,0]
        self.light_data = np.array([], dtype=np.float32)
        self.light_data_count = 0
        self.light_data_size = 0

        update_player((self.player[0], self.player[1]))

    def update(self, dt: float) -> None:
        """
            Update all objects in the scene.

            Parameters:

                dt: framerate correction factor
        """

        update_positions(
            instance_types = self.instance_types,
            positions = (self.positions[0], self.positions[1]),
            transforms = (self.model_transforms[0], self.model_transforms[1]),
            light_data = self.light_data,
            count = self.position_count
        )

        update_eulers(
            eulers = self.eulers[1],
            transforms = self.model_transforms[0],
            count = self.euler_count, rate = dt
        )

        update_lights(
            lights = (self.lights[0], self.lights[1]),
            light_data = self.light_data,
            count = self.light_count
        )

        update_player((self.player[0], self.player[1]))

    def move_player(self, d_pos: list[float]) -> None:
        """
            move the player by the given amount in the 
            (forwards, right, up) vectors.
        """

        move_player(self.player[0], d_pos)
    
    def spin_player(self, d_eulers: list[float]) -> None:
        """
            spin the player by the given amount
            around the (x,y,z) axes
        """

        spin_player(self.player[0], d_eulers)
#endregion
###############################################################################