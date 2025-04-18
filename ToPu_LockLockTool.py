bl_info = {
    "name": "ToPu_LockLockTool",
    "author": "ToPu",
    "version": (1, 0),
    "blender": (4, 0, 0),
    'tracker_url': 'https://github.com/http4211/ToPu_LockLockTool',
    "description": "Toggle object selectability or hide selected vertices in edit mode",
}

import bpy
import rna_keymap_ui

addon_keymaps = []

# オブジェクトモード：選択可否切替 / 編集モード：頂点非表示
class OBJECT_OT_toggle_select_or_hide_vertices(bpy.types.Operator):
    bl_idname = "object.toggle_select_or_hide_vertices"
    bl_label = "Toggle Selectability or Hide Vertices"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.mode == 'EDIT_MESH':
            hidden_total = 0

            # アクティブ含む選択中の編集モード対象オブジェクト取得
            edit_objs = [obj for obj in context.selected_objects if obj.type == 'MESH']

            # 選択頂点インデックスだけ記録
            selected_indices_map = {}
            for obj in edit_objs:
                bpy.context.view_layer.objects.active = obj
                obj.update_from_editmode()
                selected_indices = [v.index for v in obj.data.vertices if v.select]
                selected_indices_map[obj.name] = selected_indices

            # 一括で編集モード終了（ここで選択情報は無効になる）
            bpy.ops.object.mode_set(mode='OBJECT')

            # 各オブジェクトの頂点を非表示に
            for obj in edit_objs:
                indices = selected_indices_map.get(obj.name, [])
                for i in indices:
                    obj.data.vertices[i].hide = True
                    hidden_total += 1

            # 編集モードに復帰（アクティブを復元）
            if edit_objs:
                bpy.context.view_layer.objects.active = edit_objs[0]
            bpy.ops.object.mode_set(mode='EDIT')

            self.report({'INFO'}, f"{hidden_total} vertices locked")
            return {'FINISHED'}

        else:
            for obj in context.selected_objects:
                obj.hide_select = not obj.hide_select
                if obj.hide_select:
                    if "_original_alpha" not in obj:
                        obj["_original_alpha"] = obj.color[3]
                    obj.color[3] = obj["_original_alpha"] * 0.2
                else:
                    if "_original_alpha" in obj:
                        obj.color[3] = obj["_original_alpha"]
                        del obj["_original_alpha"]
                self.report({'INFO'}, f"Selected objects are locked")
            return {'FINISHED'}

# 全解除：選択可否解除＋頂点の非表示も解除
class OBJECT_OT_reset_all_locks_and_hides(bpy.types.Operator):
    bl_idname = "object.reset_all_locks_and_hides"
    bl_label = "Reset Selectability and Show Vertices"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.mode == 'EDIT_MESH':
            # 編集中の対象オブジェクト（複数対応）
            edit_objs = [obj for obj in context.selected_objects if obj.type == 'MESH']

            bpy.ops.object.mode_set(mode='OBJECT')

            for obj in edit_objs:
                for v in obj.data.vertices:
                    v.hide = False

            # 編集モードに戻す（最初のオブジェクトをアクティブに）
            if edit_objs:
                bpy.context.view_layer.objects.active = edit_objs[0]
            bpy.ops.object.mode_set(mode='EDIT')

            self.report({'INFO'}, "Vertices of the object being edited have been locked")

        else:
            # 編集モード以外のときは、選択不可とalphaの解除のみ
            for obj in bpy.data.objects:
                obj.hide_select = False
                if "_original_alpha" in obj:
                    obj.color[3] = obj["_original_alpha"]
                    del obj["_original_alpha"]

            self.report({'INFO'}, "All objects are unlocked and alpha removed")

        return {'FINISHED'}

#選択以外のロック機能追加
class OBJECT_OT_lock_unselected_objects_and_vertices(bpy.types.Operator):
    bl_idname = "object.lock_unselected_objects_and_vertices"
    bl_label = "Lock Unselected Objects and Vertices"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.mode == 'EDIT_MESH':
            locked_total = 0
            edit_objs = [obj for obj in context.selected_objects if obj.type == 'MESH']

            selected_indices_map = {}
            for obj in edit_objs:
                bpy.context.view_layer.objects.active = obj
                obj.update_from_editmode()
                selected_indices = [v.index for v in obj.data.vertices if v.select]
                selected_indices_map[obj.name] = selected_indices

            bpy.ops.object.mode_set(mode='OBJECT')

            for obj in edit_objs:
                all_indices = set(range(len(obj.data.vertices)))
                selected_indices = set(selected_indices_map.get(obj.name, []))
                hidden_indices = all_indices - selected_indices
                for i in hidden_indices:
                    obj.data.vertices[i].hide = True
                    locked_total += 1

            if edit_objs:
                bpy.context.view_layer.objects.active = edit_objs[0]
            bpy.ops.object.mode_set(mode='EDIT')

            self.report({'INFO'}, f"Unselected{locked_total} vertices locked")
            return {'FINISHED'}

        else:
            for obj in bpy.data.objects:
                obj.hide_select = obj not in context.selected_objects
                if obj.hide_select:
                    if "_original_alpha" not in obj:
                        obj["_original_alpha"] = obj.color[3]
                    obj.color[3] = obj["_original_alpha"] * 0.2
                else:
                    if "_original_alpha" in obj:
                        obj.color[3] = obj["_original_alpha"]
                        del obj["_original_alpha"]
            self.report({'INFO'}, "Unselected objects locked")
            return {'FINISHED'}


class ToggleSelectabilityPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    def draw(self, context):
        layout = self.layout
        layout.label(text="Keymap List", icon="KEYINGSET")

        box = layout.box()
        col = box.column()

        wm = bpy.context.window_manager
        kc = wm.keyconfigs.user
        old_km_name = ""
        get_kmi_l = []

        for km_add, kmi_add in addon_keymaps:
            for km_con in kc.keymaps:
                if km_add.name == km_con.name:
                    km = km_con
                    break
            for kmi_con in km.keymap_items:
                if kmi_add.idname == kmi_con.idname and kmi_add.name == kmi_con.name:
                    get_kmi_l.append((km, kmi_con))

        get_kmi_l = sorted(set(get_kmi_l), key=get_kmi_l.index)

        for km, kmi in get_kmi_l:
            if km.name != old_km_name:
                col.label(text=str(km.name), icon="DOT")
            col.context_pointer_set("keymap", km)
            rna_keymap_ui.draw_kmi([], kc, km, kmi, col, 0)
            col.separator()
            old_km_name = km.name

def register():
    bpy.utils.register_class(ToggleSelectabilityPreferences)
    bpy.utils.register_class(OBJECT_OT_toggle_select_or_hide_vertices)
    bpy.utils.register_class(OBJECT_OT_reset_all_locks_and_hides)
    bpy.utils.register_class(OBJECT_OT_lock_unselected_objects_and_vertices)



    wm = bpy.context.window_manager
    if wm.keyconfigs.addon:
        kc = wm.keyconfigs.addon
        for name in ["Object Mode", "Mesh"]:
            km = kc.keymaps.new(name=name, space_type='EMPTY')
            kmi = km.keymap_items.new("object.toggle_select_or_hide_vertices", type='FOUR', value='PRESS')
            addon_keymaps.append((km, kmi))

            kmi_alt = km.keymap_items.new("object.reset_all_locks_and_hides", type='FOUR', value='PRESS', alt=True)
            addon_keymaps.append((km, kmi_alt))

            kmi_ctrl = km.keymap_items.new("object.lock_unselected_objects_and_vertices", type='FOUR', value='PRESS', ctrl=True)
            addon_keymaps.append((km, kmi_ctrl))

def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    bpy.utils.unregister_class(OBJECT_OT_reset_all_locks_and_hides)
    bpy.utils.unregister_class(OBJECT_OT_toggle_select_or_hide_vertices)
    bpy.utils.unregister_class(ToggleSelectabilityPreferences)
    bpy.utils.unregister_class(OBJECT_OT_lock_unselected_objects_and_vertices)


if __name__ == "__main__":
    register()
