import React, { useState, useEffect } from 'react';
import axios from 'axios';
import TaskCard from './TaskCard';
import TaskModal from './TaskModal';

function Board() {
    const [tasks, setTasks] = useState([]);
    const [search, setSearch] = useState('');
    const [searchResult, setSearchResult] = useState('');
    const [selectedTask, setSelectedTask] = useState(null);
    const [newTaskTitle, setNewTaskTitle] = useState('');
    const [newTaskDescription, setNewTaskDescription] = useState('');

    useEffect(() => {
        fetchTasks();
    }, []);

    const fetchTasks = async (query = '') => {
        try {
            const res = await axios.get(`/api/tasks?search=${query}`);
            setTasks(res.data.tasks);
            if (res.data.search_query) {
                // Vulnerability 9: Reflected Search Query
                // We intentionally set this to be rendered dangerously in the UI
                setSearchResult(res.data.search_query);
            } else {
                setSearchResult('');
            }
        } catch (err) {
            console.error(err);
        }
    };

    const handleSearch = (e) => {
        e.preventDefault();
        fetchTasks(search);
    };

    const handleCreateTask = async (e) => {
        e.preventDefault();
        if (!newTaskTitle) return;
        try {
            await axios.post('/api/tasks', {
                title: newTaskTitle,
                description: newTaskDescription,
                status: 'todo'
            });
            setNewTaskTitle('');
            setNewTaskDescription('');
            fetchTasks();
        } catch (err) {
            console.error(err);
        }
    };

    const columns = {
        todo: tasks.filter(t => t.status === 'todo'),
        inprogress: tasks.filter(t => t.status === 'inprogress'),
        done: tasks.filter(t => t.status === 'done')
    };

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                <form onSubmit={handleSearch} style={{ display: 'flex', gap: 10 }}>
                    <input
                        type="text"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        placeholder="Search tasks..."
                    />
                    <button type="submit" className="btn">Search</button>
                </form>

                {/* Vulnerability 9: Reflected XSS */}
                {searchResult && (
                    <div className="search-result">
                        Results for: <span dangerouslySetInnerHTML={{ __html: searchResult }}></span>
                    </div>
                )}

                <form onSubmit={handleCreateTask} style={{ display: 'flex', gap: 10 }}>
                    <input
                        type="text"
                        value={newTaskTitle}
                        onChange={(e) => setNewTaskTitle(e.target.value)}
                        placeholder="New Task Title"
                    />
                    <input
                        type="text"
                        value={newTaskDescription}
                        onChange={(e) => setNewTaskDescription(e.target.value)}
                        placeholder="New Task Description"
                    />
                    <button type="submit" className="btn">Add Task</button>
                </form>
            </div>

            <div className="board">
                {Object.entries(columns).map(([status, list]) => (
                    <div key={status} className="column">
                        <div className="column-header">{status.toUpperCase()}</div>
                        {list.map(task => (
                            <TaskCard key={task.id} task={task} onClick={() => setSelectedTask(task)} />
                        ))}
                    </div>
                ))}
            </div>

            {selectedTask && (
                <TaskModal
                    task={selectedTask}
                    onClose={() => setSelectedTask(null)}
                    onUpdate={fetchTasks}
                />
            )}
        </div>
    );
}

export default Board;
