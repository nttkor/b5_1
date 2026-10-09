"""이중 연결 리스트.

sentinel(더미) head/tail 노드를 두어 삽입/삭제 시 None 분기 없이
모든 연산을 O(1)로 처리한다. 해시맵의 버킷 체이닝과 LRU 순서 추적에 재사용된다.
"""


class Node:
    __slots__ = ("data", "prev", "next")

    def __init__(self, data=None):
        self.data = data
        self.prev = None
        self.next = None


class DoublyLinkedList:
    def __init__(self):
        self._head = Node()
        self._tail = Node()
        self._head.next = self._tail
        self._tail.prev = self._head
        self._size = 0

    def insert_front(self, data):
        node = Node(data)
        self._link_after(self._head, node)
        self._size += 1
        return node

    def insert_back(self, data):
        node = Node(data)
        self._link_after(self._tail.prev, node)
        self._size += 1
        return node

    def remove_front(self):
        if self._size == 0:
            return None
        node = self._head.next
        self.remove_node(node)
        return node.data

    def remove_back(self):
        if self._size == 0:
            return None
        node = self._tail.prev
        self.remove_node(node)
        return node.data

    def remove_node(self, node):
        node.prev.next = node.next
        node.next.prev = node.prev
        node.prev = None
        node.next = None
        self._size -= 1

    def move_to_front(self, node):
        node.prev.next = node.next
        node.next.prev = node.prev
        self._link_after(self._head, node)

    def _link_after(self, anchor, node):
        node.next = anchor.next
        node.prev = anchor
        anchor.next.prev = node
        anchor.next = node

    def __len__(self):
        return self._size

    def __iter__(self):
        node = self._head.next
        while node is not self._tail:
            yield node.data
            node = node.next

    def nodes(self):
        """노드 자체를 순회한다(해시맵이 체이닝된 버킷에서 특정 노드를 찾아 지우기 위함)."""
        node = self._head.next
        while node is not self._tail:
            nxt = node.next
            yield node
            node = nxt
