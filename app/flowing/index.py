from app.common.utils import log_request_error
from app.models import db, Student, Project
from app.pdf_storage import upload

from flask import current_app, jsonify
from flask.ext.restful import Resource
from PyPDF2 import PdfFileWriter, PdfFileReader
from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

import math
import os
import requests
from cStringIO import StringIO


Image.MAX_IMAGE_PIXELS = None

# Nasty Globals
file_path = os.path.abspath(__file__)
folder_path = file_path.rsplit(os.path.sep, 2)[0]
DESIRED_DPI = 72
segments_folder = "pspa_proof_segments"
# -------------
# Set up temp folder if it doesn't exist
folder_check = os.path.join(folder_path, "pspa_proof_segments")
if not os.path.exists(folder_check):
    os.makedirs(folder_check)
# -------------


def build_index(project_number, field, n_reversed, c_reversed, user_id, token, category):
    try:
        print "Starting directory proof for project " + project_number
        project = db.session.query(Project).filter_by(project_uuid=project_number).first()
        project_id = project.project_id

        raw_student_list = db.session.query(Student).filter_by(project_id=project_id, student_omitted=False,
                                                               is_deleted=False).all()

        if field == "first":
            first_sort = sorted(raw_student_list, key=lambda g: (g.student_first_name, g.student_last_name),
                                reverse=n_reversed)
            print_order = ["student_first_name", "student_last_name"]
        else:
            first_sort = sorted(raw_student_list, key=lambda g: (g.student_last_name, g.student_first_name),
                                reverse=n_reversed)
            print_order = ["student_last_name", "student_first_name"]

        second_sort = sorted(first_sort, key=lambda g: (getattr(g, category)), reverse=c_reversed)

        list_of_groups = sorted(set(getattr(x, category) for x in second_sort))
        group_item_count = {}
        for group in list_of_groups:
            group_item_count[group] = sum(1 for p in second_sort if getattr(p, category) == group and
                                          not p.student_omitted)
        page_height = 11 * 72
        page_width = int(8.5 * 72)

        rows = 9
        columns = 9

        margin = .5 * 72  # half an inch marge around the page

        text_width = (page_width - margin * 2) / columns
        group_height = (page_height - margin * 2) / rows

        text_height = 8 * 1.1715 * 2
        image_height = group_height - text_height
        image_width = image_height / 5 * 4
        image_x_offset = (text_width - image_width) / 2

        _headers_ = {"user-id": user_id, "project-id": project_number, "x-subject-token": token}

        _canvas = canvas.Canvas(os.path.join(folder_path, segments_folder,
                                             project.project_number + "_pspa_proof_1.pdf"),
                                pagesize=(page_width, page_height))

        count = 1
        page_count = 1
        ratio = 150.0/72.0
        current_group = getattr(second_sort[0], category)
        for num, person in enumerate(second_sort):
            if person.student_omitted:
                continue
            new_group = getattr(person, category)
            if current_group != new_group:
                current_group = new_group
                _canvas.save()
                page_count += 1
                _canvas = canvas.Canvas(os.path.join(folder_path, segments_folder,
                                                     project.project_number + "_pspa_proof_%s.pdf" % str(page_count)),
                                        pagesize=(page_width, page_height))
                count = 1
                pass

            if count == 1:
                _canvas.setFont(psfontname="Helvetica", size=12)
                title = getattr(person, category) + " (" + str(group_item_count[getattr(person, category)]) + " people)"
                _canvas.drawCentredString(x=page_width/2, y=page_height - margin + 12 * 1.1715,
                                          text=title)
            url = current_app.config["IMAGE_REPO"] + "/images/blob/" + str(person.image_id)
            resp = requests.get(url, headers=_headers_, verify=False, stream=True)
            # If image isn't found, because it's been deleted, skip it.
            if resp.status_code == 404:
                url = current_app.config["MISSING_PHOTO_URL"]
                resp = requests.get(url, headers=_headers_)
            elif resp.status_code != 200:
                break

            modified_height = int(math.ceil(image_height * ratio))
            modified_width = int(math.ceil(image_width * ratio))

            base_image = Image.open(StringIO(resp.content))
            base_image = base_image.resize((modified_width, modified_height), Image.ANTIALIAS)
            image = ImageReader(base_image)

            image_x = margin + (text_width * ((count - 1) % 9)) + image_x_offset
            image_y = page_height - margin - group_height - group_height * ((count - 1) / 9)
            _canvas.drawImage(image=image, x=image_x, y=image_y,
                              width=image_width, height=image_height, mask="auto")

            default_text_size = 8
            _canvas.setFont(psfontname="Helvetica", size=default_text_size)
            name = getattr(person, print_order[0])
            while _canvas.stringWidth(name) > text_width:
                default_text_size -= 1
                _canvas.setFont(psfontname="Helvetica", size=default_text_size)
            _canvas.drawCentredString(x=image_x + image_width / 2, y=image_y - text_height * .4,
                                      text=getattr(person, print_order[0]))
            default_text_size = 8
            _canvas.setFont(psfontname="Helvetica", size=default_text_size)
            name = getattr(person, print_order[1])
            while _canvas.stringWidth(name) > text_width:
                default_text_size -= 1
                _canvas.setFont(psfontname="Helvetica", size=default_text_size)
            _canvas.drawCentredString(x=image_x + image_width / 2, y=image_y - text_height * .9,
                                      text=getattr(person, print_order[1]))

            if count % (rows * columns) == 0:
                current_group = new_group
                _canvas.save()
                page_count += 1
                _canvas = canvas.Canvas(os.path.join(folder_path, segments_folder,
                                                     project.project_number + "_pspa_proof_%s.pdf" % str(page_count)),
                                        pagesize=(page_width, page_height))
                count = 0
                print project_number, "directory proof", float(num) / len(second_sort) * 100, "percent complete"
            count += 1

        _canvas.save()

        output = PdfFileWriter()

        for each in xrange(0, page_count):
            path = os.path.join(folder_path, segments_folder,
                                project.project_number + "_pspa_proof_%s.pdf" % str(each + 1))
            temp_pdf = PdfFileReader(file(path, "rb"))
            output.addPage(temp_pdf.getPage(0))
            os.remove(path)

        full_path = os.path.join(folder_path, segments_folder, project.project_number + "_pspa_proof.pdf")
        output_stream = file(full_path, "wb")
        output.write(output_stream)
        output_stream.close()

        url_in_s3 = upload(local_path=full_path,
                           pdf_name=project_number + '/' + project.project_number + "_directory_proof.pdf")

        os.remove(full_path)
        print "Finished directory proof for project " + project_number
        return url_in_s3

    except Exception as Ex:
        log_request_error("Failed to generate directory proof for project " + project_number, Ex)


class Index(Resource):

    def post(self, **kwargs):
        data = {"Error": "This should only be done over websockets."}
        resp = jsonify(data)
        resp.status_code = 400
        return resp


class AvailableGroups(Resource):

    def get(self, project_id):
        # Yes I know everything returns a 200. Thanks MyYear.
        # Switch out the uuid project_id for the b4pub int project_id.
        project = db.session.query(Project).filter_by(project_uuid=project_id).first()
        if not project:
            return self.resp({"error": "project not found"})
        # Grab 3 students in case one or 2 are messed up/not added to groups properly.
        students = db.session.query(Student).filter_by(project_id=project.project_id, student_omitted=0).limit(3)
        if students.count() == 0:
            return self.resp({"error": "no students found"})
        active_groups = []
        for student in students:
            for group in ["student_grade", "student_teacher", "student_homeroom", "student_period"]:
                if getattr(student, group) and getattr(student, group) != "":
                    active_groups.append(group)
        if len(active_groups) > 0:
            # Return unique entries.
            return self.resp({"groups": list(set(active_groups))})

        else:
            return self.resp({"error": "no groups found"})

    def resp(self, data):
        resp = jsonify(data)
        resp.status_code = 200
        return resp
