"""
Dataset Creator Service
Handles character constraints, dataset management, and dynamic caption generation
"""
import os
import uuid
from typing import List, Dict, Optional
import psycopg2
import psycopg2.extras
from datetime import datetime
import json

DATABASE_URL = os.getenv('DIRECT_DATABASE_URL')

class DatasetService:
    def __init__(self):
        self.db_url = DATABASE_URL

    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url)

    # ========================================================================
    # CHARACTER CONSTRAINTS
    # ========================================================================

    def get_character_with_constraints(self, character_id: str) -> Optional[Dict]:
        """Get character including constraints"""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        try:
            cur.execute("""
                SELECT
                    id, name, trigger_word, description, thumbnail_url,
                    character_constraints, lora_file, is_active,
                    created_at, updated_at
                FROM characters
                WHERE id = %s
            """, (character_id,))

            character = cur.fetchone()
            if character:
                return dict(character)
            return None
        finally:
            cur.close()
            conn.close()

    def update_character_constraints(
        self,
        character_id: str,
        constraints: Dict
    ) -> bool:
        """Update character constraints"""
        conn = self.get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                UPDATE characters
                SET character_constraints = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (json.dumps(constraints), character_id))

            conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error updating character constraints: {e}")
            return False
        finally:
            cur.close()
            conn.close()

    def add_character_constraint(
        self,
        character_id: str,
        key: str,
        value: str,
        constraint_type: str = "physical"
    ) -> bool:
        """Add or update a single constraint"""
        character = self.get_character_with_constraints(character_id)
        if not character:
            return False

        constraints = character.get('character_constraints') or {"constants": []}
        if not isinstance(constraints, dict):
            constraints = {"constants": []}

        # Initialize constants array if missing
        if 'constants' not in constraints:
            constraints['constants'] = []

        # Check if constraint exists
        existing = [c for c in constraints['constants'] if c.get('key') == key]
        if existing:
            # Update existing
            for c in constraints['constants']:
                if c.get('key') == key:
                    c['value'] = value
                    c['type'] = constraint_type
        else:
            # Add new
            constraints['constants'].append({
                'key': key,
                'value': value,
                'type': constraint_type
            })

        return self.update_character_constraints(character_id, constraints)

    def remove_character_constraint(self, character_id: str, key: str) -> bool:
        """Remove a constraint from character"""
        character = self.get_character_with_constraints(character_id)
        if not character:
            return False

        constraints = character.get('character_constraints') or {"constants": []}
        if not isinstance(constraints, dict):
            return False

        # Filter out the constraint
        constraints['constants'] = [
            c for c in constraints.get('constants', [])
            if c.get('key') != key
        ]

        return self.update_character_constraints(character_id, constraints)

    # ========================================================================
    # TRAINING DATASETS
    # ========================================================================

    def create_training_dataset(
        self,
        character_id: str,
        name: str,
        dataset_type: str,
        description: Optional[str] = None,
        dataset_constraints: Optional[Dict] = None
    ) -> Optional[str]:
        """Create a new training dataset"""
        conn = self.get_connection()
        cur = conn.cursor()

        dataset_id = str(uuid.uuid4())

        try:
            cur.execute("""
                INSERT INTO training_datasets (
                    id, character_id, name, dataset_type, description,
                    dataset_constraints, image_count, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, 0, NOW(), NOW())
                RETURNING id
            """, (
                dataset_id,
                character_id,
                name,
                dataset_type,
                description,
                json.dumps(dataset_constraints or {"rules": []})
            ))

            conn.commit()
            return dataset_id
        except Exception as e:
            conn.rollback()
            print(f"Error creating training dataset: {e}")
            return None
        finally:
            cur.close()
            conn.close()

    def get_dataset(self, dataset_id: str) -> Optional[Dict]:
        """Get training dataset"""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        try:
            cur.execute("""
                SELECT *
                FROM training_datasets
                WHERE id = %s
            """, (dataset_id,))

            dataset = cur.fetchone()
            if dataset:
                return dict(dataset)
            return None
        finally:
            cur.close()
            conn.close()

    def get_character_datasets(self, character_id: str) -> List[Dict]:
        """Get all datasets for a character"""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        try:
            cur.execute("""
                SELECT *
                FROM training_datasets
                WHERE character_id = %s
                ORDER BY created_at DESC
            """, (character_id,))

            datasets = cur.fetchall()
            return [dict(d) for d in datasets]
        finally:
            cur.close()
            conn.close()

    def update_dataset_constraints(
        self,
        dataset_id: str,
        constraints: Dict
    ) -> bool:
        """Update dataset constraints"""
        conn = self.get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                UPDATE training_datasets
                SET dataset_constraints = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (json.dumps(constraints), dataset_id))

            conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error updating dataset constraints: {e}")
            return False
        finally:
            cur.close()
            conn.close()

    # ========================================================================
    # TRAINING IMAGES
    # ========================================================================

    def add_training_image(
        self,
        dataset_id: str,
        image_url: str,
        caption: str,
        metadata: Optional[Dict] = None,
        display_order: int = 0
    ) -> Optional[str]:
        """Add a training image to dataset"""
        conn = self.get_connection()
        cur = conn.cursor()

        image_id = str(uuid.uuid4())

        try:
            cur.execute("""
                INSERT INTO training_images (
                    id, dataset_id, image_url, caption, metadata,
                    display_order, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
            """, (
                image_id,
                dataset_id,
                image_url,
                caption,
                json.dumps(metadata or {}),
                display_order
            ))

            # Update image count in dataset
            cur.execute("""
                UPDATE training_datasets
                SET image_count = image_count + 1,
                    updated_at = NOW()
                WHERE id = %s
            """, (dataset_id,))

            conn.commit()
            return image_id
        except Exception as e:
            conn.rollback()
            print(f"Error adding training image: {e}")
            return None
        finally:
            cur.close()
            conn.close()

    def get_dataset_images(self, dataset_id: str) -> List[Dict]:
        """Get all images for a dataset"""
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        try:
            cur.execute("""
                SELECT *
                FROM training_images
                WHERE dataset_id = %s
                ORDER BY display_order, created_at
            """, (dataset_id,))

            images = cur.fetchall()
            return [dict(img) for img in images]
        finally:
            cur.close()
            conn.close()

    def update_training_image_caption(
        self,
        image_id: str,
        caption: str
    ) -> bool:
        """Update caption for a training image"""
        conn = self.get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                UPDATE training_images
                SET caption = %s
                WHERE id = %s
            """, (caption, image_id))

            conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error updating caption: {e}")
            return False
        finally:
            cur.close()
            conn.close()

    def delete_training_image(self, image_id: str) -> bool:
        """Delete a training image"""
        conn = self.get_connection()
        cur = conn.cursor()

        try:
            # Get dataset_id first
            cur.execute("""
                SELECT dataset_id FROM training_images WHERE id = %s
            """, (image_id,))
            result = cur.fetchone()

            if not result:
                return False

            dataset_id = result[0]

            # Delete image
            cur.execute("""
                DELETE FROM training_images WHERE id = %s
            """, (image_id,))

            # Update count
            cur.execute("""
                UPDATE training_datasets
                SET image_count = image_count - 1,
                    updated_at = NOW()
                WHERE id = %s
            """, (dataset_id,))

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error deleting training image: {e}")
            return False
        finally:
            cur.close()
            conn.close()

    # ========================================================================
    # DYNAMIC PROMPT BUILDING
    # ========================================================================

    def build_caption_format(
        self,
        character: Dict,
        dataset: Optional[Dict] = None
    ) -> str:
        """Build caption format string from constraints"""
        trigger = character.get('trigger_word', character['id'])

        constraints = character.get('character_constraints') or {}
        if isinstance(constraints, str):
            try:
                constraints = json.loads(constraints)
            except:
                constraints = {}

        constants = constraints.get('constants', [])

        # Build constants string
        const_parts = [c['value'] for c in constants if isinstance(c, dict) and 'value' in c]
        const_str = ", ".join(const_parts) if const_parts else ""

        # Build format
        if const_str:
            format_str = f"{trigger}, a woman with {const_str}"
        else:
            format_str = f"{trigger}, a woman"

        # Add variable placeholders
        format_str += ", {{hair_style}}, wearing {{clothing}}, {{action}}, {{setting}}"

        return format_str

    def build_grok_prompt(
        self,
        character: Dict,
        dataset: Optional[Dict] = None
    ) -> str:
        """Build dynamic Grok prompt from character and dataset constraints"""
        trigger = character.get('trigger_word', character['id'])

        # Get character constants
        constraints = character.get('character_constraints') or {}
        if isinstance(constraints, str):
            try:
                constraints = json.loads(constraints)
            except:
                constraints = {}

        constants = constraints.get('constants', [])
        const_desc = ", ".join([c['value'] for c in constants if isinstance(c, dict) and 'value' in c])

        # Get dataset rules
        dataset_rules = "- None"
        if dataset:
            dataset_constraints = dataset.get('dataset_constraints') or {}
            if isinstance(dataset_constraints, str):
                try:
                    dataset_constraints = json.loads(dataset_constraints)
                except:
                    dataset_constraints = {}

            rules = dataset_constraints.get('rules', [])
            if rules:
                dataset_rules = "\n".join([f"- {r['key']}: {r['value']}" for r in rules if isinstance(r, dict)])

        # Build caption format
        caption_format = self.build_caption_format(character, dataset)

        # Build full prompt
        prompt = f"""Generate a training caption for this image.

CAPTION STRUCTURE:
{caption_format}

REQUIRED ELEMENTS (must include exactly as written):
- Trigger word: "{trigger}" (MUST be the first word)
- Character constants: {const_desc if const_desc else "none specified"}

DATASET RULES:
{dataset_rules}

VARIABLE ELEMENTS (describe what you see in the image):
- Hair style: How is the hair styled? (down in waves, ponytail, bun, braided, etc.)
- Clothing: What is the subject wearing? Be specific.
- Action/Pose: What is the subject doing? Their pose?
- Setting: Where is this? What's the background?
- Lighting/Mood: Describe the atmosphere and lighting

IMPORTANT:
- Keep the caption natural and flowing, not robotic
- Always start with "{trigger}"
- Include all character constants
- Be accurate to what you see in the image
- Keep it concise but descriptive (1-2 sentences)

Generate the caption now (just the caption, no explanation):"""

        return prompt
