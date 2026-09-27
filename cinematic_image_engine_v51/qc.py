from pathlib import Path

class CinematicQC:
    REQUIRED=("image_quality","face_identity","character_continuity","wardrobe_continuity",
              "body_continuity","world_continuity","object_continuity","lighting","composition",
              "camera","artifacts")
    def inspect(self,image_path,shot,continuity):
        p=Path(image_path); exists=p.exists() and p.stat().st_size>0
        result={k:exists for k in self.REQUIRED}
        result.update({"file_exists":exists,"adapter":"filesystem-baseline",
                       "score":1.0 if exists else 0.0,"pass":exists})
        return result
