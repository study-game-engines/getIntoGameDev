#include "obj_mesh.h"

ObjMesh::ObjMesh(util::MeshCreateInfo* createInfo) {

	unpackData(
		util::load_model_from_file(createInfo)
	);
	//std::cout << elementCount << std::endl;
	elementCount = static_cast<uint32_t>(indices.size());
	glCreateBuffers(1, &VBO);
	glCreateBuffers(1, &EBO);
	glCreateVertexArrays(1, &VAO);
	glVertexArrayVertexBuffer(VAO, 0, VBO, 0, 8 * sizeof(float));
	glNamedBufferStorage(
		VBO, vertices.size() * sizeof(float), vertices.data(), GL_DYNAMIC_STORAGE_BIT
	);
	glVertexArrayElementBuffer(VAO, EBO);
	glNamedBufferStorage(
		EBO, indices.size() * sizeof(uint32_t), indices.data(), GL_DYNAMIC_STORAGE_BIT
	);
	//pos: 0, texcoord: 1, normal: 2
	glEnableVertexArrayAttrib(VAO, 0);
	glEnableVertexArrayAttrib(VAO, 1);
	glEnableVertexArrayAttrib(VAO, 2);
	glVertexArrayAttribFormat(VAO, 0, 3, GL_FLOAT, GL_FALSE, 0);
	glVertexArrayAttribFormat(VAO, 1, 2, GL_FLOAT, GL_FALSE, 3 * sizeof(float));
	glVertexArrayAttribFormat(VAO, 2, 3, GL_FLOAT, GL_FALSE, 5 * sizeof(float));
	glVertexArrayAttribBinding(VAO, 0, 0);
	glVertexArrayAttribBinding(VAO, 1, 0);
	glVertexArrayAttribBinding(VAO, 2, 0);
}

void ObjMesh::unpackData(util::ModelData modelData) {

	for (util::Vertex vertex : modelData.vertices) {
		vertices.push_back(vertex.pos.x);
		vertices.push_back(vertex.pos.y);
		vertices.push_back(vertex.pos.z);
		//std::cout << "pos: (" << vertex.pos.x << ", " << vertex.pos.y << ", " << vertex.pos.z << ")" << std::endl;
		vertices.push_back(vertex.texCoord.x);
		vertices.push_back(vertex.texCoord.y);
		//std::cout << "tex coord: (" << vertex.texCoord.x << ", " << vertex.texCoord.y << ")" << std::endl;
		vertices.push_back(vertex.normal.x);
		vertices.push_back(vertex.normal.y);
		vertices.push_back(vertex.normal.z);
		//std::cout << "normal: (" << vertex.normal.x << ", " << vertex.normal.y << ", " << vertex.normal.z << ")" << std::endl;
	}

	for (uint32_t index : modelData.indices) {
		indices.push_back(index);
		//std::cout << index << std::endl;
	}
}

ObjMesh::~ObjMesh() {
	glDeleteBuffers(1, &VBO);
	glDeleteBuffers(1, &EBO);
	glDeleteVertexArrays(1, &VAO);
}