from tests.unit import unittest, AWSMockServiceTestCase

from boto.ec2.connection import EC2Connection
from boto.ec2.import_task import ImportImageTask, ImportSnapshotTask
from boto.ec2.export_task import ExportTask, ExportVolumeTask


class BaseTestImportExport(AWSMockServiceTestCase):
    connection_class = EC2Connection

    TASK_ID = "i-task"
    ignore_params_values = ["AWSAccessKeyId", "SignatureVersion", "SignatureMethod", "Timestamp", "Version"]


class TestImportImage(BaseTestImportExport):

    def default_body(self):
        return r"""
        <ImportImageResponse xmlns="http://ec2.amazonaws.com/doc/2012-06-01/">
            <item>
                <importTaskId>{task_id}</importTaskId>
                <snapshotDetails>
                    <item>
                        <snapshotId>i-snapshot1</snapshotId>
                    </item>
                    <item>
                        <snapshotId>i-snapshot2</snapshotId>
                    </item>
                </snapshotDetails>
            </item>
        </ImportImageResponse>
        """.format(task_id=self.TASK_ID)

    def test_import_image(self):
        self.set_http_response(status_code=200)

        task = self.service_connection.import_image(
            [
                {"Format": "RAW", "UserBucket": {"S3Bucket": "bucket1", "S3Key": "key1"}},
                {"Format": "VMDK", "UserBucket": {"S3Bucket": "bucket2", "S3Key": "key2"}},
            ],
            description="description", architecture="architecture", platform="platform"
        )
        self.assert_request_parameters({
            "Action": "ImportImage",
            "DiskContainer.1.Format": "RAW",
            "DiskContainer.1.UserBucket.S3Bucket": "bucket1",
            "DiskContainer.1.UserBucket.S3Key": "key1",
            "DiskContainer.2.Format": "VMDK",
            "DiskContainer.2.UserBucket.S3Bucket": "bucket2",
            "DiskContainer.2.UserBucket.S3Key": "key2",
            "Description": "description",
            "Architecture": "architecture",
            "Platform": "platform"
        }, self.ignore_params_values)

        self.assertIsInstance(task, ImportImageTask)
        self.assertEqual(task.id, self.TASK_ID)
        self.assertEqual(len(task.snapshot_details), 2)
        self.assertEqual(task.snapshot_details[0].snapshot_id, "i-snapshot1")
        self.assertEqual(task.snapshot_details[1].snapshot_id, "i-snapshot2")

    def test_describe_import_image_tasks(self):
        self.set_http_response(status_code=200)
        tasks = self.service_connection.describe_import_image_tasks([self.TASK_ID])
        self.assert_request_parameters({
            "Action": "DescribeImportImageTasks",
            "ImportTaskId.1": "i-task"
        }, self.ignore_params_values)

        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        self.assertIsInstance(task, ImportImageTask)
        self.assertEqual(task.id, self.TASK_ID)

    def test_cancel_import_task(self):
        self.set_http_response(status_code=200)
        task = self.service_connection.cancel_import_task(self.TASK_ID)
        self.assert_request_parameters({
            "Action": "CancelImportTask",
            "ImportTaskId": "i-task"
        }, self.ignore_params_values)

        self.assertEqual(task.importTaskId, self.TASK_ID)


class TestImportSnapshot(BaseTestImportExport):

    def default_body(self):
        return r"""
        <ImportSnapshotResponse xmlns="http://ec2.amazonaws.com/doc/2012-06-01/">
            <item>
                <importTaskId>{task_id}</importTaskId>
                <snapshotTaskDetail>
                    <snapshotId>i-snapshot1</snapshotId>
                </snapshotTaskDetail>
            </item>
        </ImportSnapshotResponse>
        """.format(task_id=self.TASK_ID)

    def test_import_snapshot(self):
        self.set_http_response(status_code=200)

        task = self.service_connection.import_snapshot(
             "bucket", "key", disk_format="VMDK", description="description",
        )
        self.assert_request_parameters({
            "Action": "ImportSnapshot",
            "DiskContainer.Url": "",
            "DiskContainer.Format": "VMDK",
            "DiskContainer.UserBucket.S3Bucket": "bucket",
            "DiskContainer.UserBucket.S3Key": "key",
            "Description": "description",
        }, self.ignore_params_values)

        self.assertIsInstance(task, ImportSnapshotTask)
        self.assertEqual(task.id, self.TASK_ID)
        self.assertEqual(task.snapshot_id, "i-snapshot1")

    def test_describe_import_snapshot_tasks(self):
        self.set_http_response(status_code=200)

        tasks = self.service_connection.describe_import_snapshot_tasks(
             [self.TASK_ID]
        )
        self.assert_request_parameters({
            "Action": "DescribeImportSnapshotTasks",
            "ImportTaskId.1": "i-task"
        }, self.ignore_params_values)

        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        self.assertIsInstance(task, ImportSnapshotTask)
        self.assertEqual(task.id, self.TASK_ID)
        self.assertEqual(task.snapshot_id, "i-snapshot1")


class TestExportTasks(BaseTestImportExport):

    def default_body(self):
        return r"""
        <ExportInstanceResponse xmlns="http://ec2.amazonaws.com/doc/2012-06-01/">
            <item>
                <exportTaskId>{task_id}</exportTaskId>
                <instanceExportDetails>
                    <instanceId>i-instance</instanceId>
                </instanceExportDetails>
                <volumeExportDetails>
                    <item>
                        <volumeId>i-volume</volumeId>
                    </item>
                </volumeExportDetails>
            </item>
        </ExportInstanceResponse>
        """.format(task_id=self.TASK_ID)

    def test_create_instance_export_task(self):
        self.set_http_response(status_code=200)

        task = self.service_connection.create_instance_export_task(
            "i-instance", "bucket",
            description="description", disk_image_format="VMDK", container_format="OVA"
        )
        self.assert_request_parameters({
            "Action": "CreateInstanceExportTask",
            "InstanceId": "i-instance",
            "ExportToS3.S3Bucket": "bucket",
            "ExportToS3.DiskImageFormat": "VMDK",
            "ExportToS3.ContainerFormat": "OVA",
            "Description": "description",
        }, self.ignore_params_values)

        self.assertIsInstance(task, ExportTask)
        self.assertEqual(task.id, self.TASK_ID)
        self.assertEqual(task.instance_id, "i-instance")


    def test_describe_export_tasks(self):
        self.set_http_response(status_code=200)
        tasks = self.service_connection.describe_export_tasks([self.TASK_ID])
        self.assert_request_parameters({
            "Action": "DescribeExportTasks",
            "ExportTaskId.1": "i-task"
        }, self.ignore_params_values)

        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        self.assertIsInstance(task, ExportTask)
        self.assertEqual(task.id, self.TASK_ID)
        self.assertEqual(task.instance_id, "i-instance")
        self.assertEqual(len(task.volume_export_details), 1)
        volume = task.volume_export_details[0]
        self.assertIsInstance(volume, ExportVolumeTask)
        self.assertEqual(volume.volume_id, "i-volume")

    def test_cancel_export_task(self):
        self.set_http_response(status_code=200)

        resp = self.service_connection.cancel_export_task(self.TASK_ID)
        self.assert_request_parameters({
            "Action": "CancelExportTask",
            "ExportTaskId": "i-task"
        }, self.ignore_params_values)
        self.assertTrue(resp)


if __name__ == "__main__":
    unittest.main()
