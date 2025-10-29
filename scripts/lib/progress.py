"""Progress tracking for workflow resumability"""

import json
from pathlib import Path
from datetime import datetime


class ProgressTracker:
    """Track workflow progress for resume capability"""

    def __init__(self, model_name):
        self.model_name = model_name
        self.progress_file = Path('models') / model_name / 'progress.json'
        self.progress = self._load()

    def _load(self):
        """Load existing progress or create new"""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        else:
            return {
                'model_name': self.model_name,
                'created_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat(),
                'stages': {
                    'upload': {'completed': False, 'timestamp': None},
                    'swap': {'completed': False, 'timestamp': None},
                    'enhance': {'completed': False, 'timestamp': None},
                    'caption': {'completed': False, 'timestamp': None}
                },
                'tasks': {}
            }

    def _save(self):
        """Save progress to file"""
        self.progress['last_updated'] = datetime.now().isoformat()
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)

    def get_task_key(self, source_id, target_id, content_type):
        """Generate unique task key"""
        return f"{content_type}_s{source_id}_t{target_id}"

    def is_completed(self, source_id, target_id, content_type, stage):
        """Check if a task stage is completed"""
        task_key = self.get_task_key(source_id, target_id, content_type)
        task = self.progress['tasks'].get(task_key, {})
        return task.get(stage, {}).get('completed', False)

    def mark_completed(self, source_id, target_id, content_type, stage, result_data=None):
        """Mark task stage as completed"""
        task_key = self.get_task_key(source_id, target_id, content_type)

        if task_key not in self.progress['tasks']:
            self.progress['tasks'][task_key] = {
                'source_id': source_id,
                'target_id': target_id,
                'content_type': content_type
            }

        self.progress['tasks'][task_key][stage] = {
            'completed': True,
            'timestamp': datetime.now().isoformat(),
            'result': result_data or {}
        }

        self._save()

    def get_pending_tasks(self, content_type, stage):
        """
        Get list of tasks pending for a specific stage

        Returns:
            list of (source_id, target_id) tuples
        """
        pending = []

        for task_key, task_data in self.progress['tasks'].items():
            if task_data['content_type'] == content_type:
                if not task_data.get(stage, {}).get('completed', False):
                    pending.append((task_data['source_id'], task_data['target_id']))

        return pending

    def initialize_tasks(self, source_ids, target_ids, content_type):
        """Initialize all task combinations"""
        for source_id in source_ids:
            for target_id in target_ids:
                task_key = self.get_task_key(source_id, target_id, content_type)
                if task_key not in self.progress['tasks']:
                    self.progress['tasks'][task_key] = {
                        'source_id': source_id,
                        'target_id': target_id,
                        'content_type': content_type
                    }

        self._save()

    def get_stats(self, content_type=None):
        """
        Get progress statistics

        Returns:
            dict with completed/total counts per stage
        """
        tasks = self.progress['tasks']
        if content_type:
            tasks = {k: v for k, v in tasks.items() if v['content_type'] == content_type}

        total = len(tasks)
        if total == 0:
            return {'total': 0, 'swap': 0, 'enhance': 0, 'caption': 0, 'swap_pct': 0, 'enhance_pct': 0, 'caption_pct': 0}

        swap_completed = sum(1 for t in tasks.values()
                           if t.get('swap', {}).get('completed', False))
        enhance_completed = sum(1 for t in tasks.values()
                              if t.get('enhance', {}).get('completed', False))
        caption_completed = sum(1 for t in tasks.values()
                              if t.get('caption', {}).get('completed', False))

        return {
            'total': total,
            'swap': swap_completed,
            'enhance': enhance_completed,
            'caption': caption_completed,
            'swap_pct': int(swap_completed / total * 100) if total > 0 else 0,
            'enhance_pct': int(enhance_completed / total * 100) if total > 0 else 0,
            'caption_pct': int(caption_completed / total * 100) if total > 0 else 0
        }

    def reset(self):
        """Reset all progress"""
        self.progress = {
            'model_name': self.model_name,
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'stages': {
                'upload': {'completed': False, 'timestamp': None},
                'swap': {'completed': False, 'timestamp': None},
                'enhance': {'completed': False, 'timestamp': None},
                'caption': {'completed': False, 'timestamp': None}
            },
            'tasks': {}
        }
        self._save()

    def clear_stage(self, stage):
        """Clear progress for specific stage"""
        for task in self.progress['tasks'].values():
            if stage in task:
                del task[stage]
        self._save()
