# 导入 DRF APIView。
from rest_framework.views import APIView

# 导入项目统一响应工具。
from common.response import ApiResponse

# 导入账户模型。
from .models import Account

# 导入账户序列化器。
from .serializers import (
    AccountBalanceAdjustSerializer,
    AccountBalanceAdjustmentSerializer,
    AccountCreateSerializer,
    AccountSerializer,
    AccountUpdateSerializer,
    TransferCreateSerializer,
    TransferSerializer,
)

# 导入账户业务服务。
from .services import AccountService


class AccountListCreateView(APIView):
    """
    账户列表 / 新增账户接口。

    GET:
        获取当前登录用户账户列表。

    POST:
        创建新的资金账户。

    请求地址：
        /api/v1/accounts/
    """

    def get(self, request):
        """
        获取当前登录用户账户列表。
        """

        # 只查询当前登录用户自己的账户。
        #
        # 不接受前端传 user_id，
        # 防止越权查询其他用户数据。
        accounts = Account.objects.filter(
            user=request.user,
            is_deleted=False,
        ).order_by(
            "sort_order",
            "id",
        )

        # 将 QuerySet 转换为接口返回数据。
        serializer = AccountSerializer(
            accounts,
            many=True,
        )

        # 返回统一成功响应。
        return ApiResponse.success(
            message="获取账户列表成功",
            data=serializer.data,
        )

    def post(self, request):
        """
        创建新的资金账户。
        """

        # 创建参数校验序列化器。
        serializer = AccountCreateSerializer(
            # 接收前端请求数据。
            data=request.data,
            # 将 request 传给 Serializer，
            # 用于获取当前登录用户。
            context={
                "request": request,
            },
        )

        # 执行参数校验。
        serializer.is_valid(raise_exception=True)

        # 调用账户 Service 创建账户。
        account = AccountService.create_account(
            # 当前登录用户。
            user=request.user,
            # 已经过校验的数据。
            validated_data=(serializer.validated_data),
        )

        # 将创建后的 Account
        # 转换成接口返回格式。
        result = AccountSerializer(account)

        # 返回统一成功响应。
        return ApiResponse.success(
            message="账户创建成功",
            data=result.data,
        )


class AccountDetailView(APIView):
    """
    账户详情接口。

    请求方式：
        GET

    请求地址：
        /api/v1/accounts/{id}/
    """

    def get(
        self,
        request,
        account_id,
    ):
        """
        获取指定账户详情。
        """

        # 调用 Service 获取账户。
        #
        # Service 内部已经保证：
        # 只能访问当前用户自己的账户。
        account = AccountService.get_account(
            user=request.user,
            account_id=account_id,
        )

        # 将账户模型转换为接口返回数据。
        serializer = AccountSerializer(account)

        # 返回统一响应。
        return ApiResponse.success(
            message="获取账户详情成功",
            data=serializer.data,
        )

    def put(
        self,
        request,
        account_id,
    ):
        """
        修改指定账户。
        """

        # 获取账户。
        account = AccountService.get_account(
            user=request.user,
            account_id=account_id,
        )

        # 参数校验。
        serializer = AccountUpdateSerializer(
            data=request.data,
            context={
                "request": request,
                "account": account,
            },
        )

        serializer.is_valid(raise_exception=True)

        # 修改账户。
        updated_account = AccountService.update_account(
            user=request.user,
            account_id=account_id,
            validated_data=(serializer.validated_data),
        )

        # 返回修改后的账户信息。
        result = AccountSerializer(updated_account)

        return ApiResponse.success(
            message="账户修改成功",
            data=result.data,
        )

    def delete(
        self,
        request,
        account_id,
    ):
        """
        删除指定账户。

        实际执行逻辑删除，
        不直接删除数据库记录。
        """

        # 调用 Service 执行账户删除。
        AccountService.delete_account(
            user=request.user,
            account_id=account_id,
        )

        # 返回统一响应。
        return ApiResponse.success(
            message="账户删除成功",
            data=None,
        )


class AccountBalanceAdjustView(APIView):
    """
    账户余额校准接口。

    请求方式：
        POST

    请求地址：
        /api/v1/accounts/{id}/adjust-balance/

    该接口必须登录后才能访问。
    """

    def post(
        self,
        request,
        account_id,
    ):
        """
        校准指定账户余额。
        """

        # 创建参数序列化器。
        serializer = AccountBalanceAdjustSerializer(data=request.data)

        # 执行参数校验。
        serializer.is_valid(raise_exception=True)

        # 获取新的实际余额。
        new_balance = serializer.validated_data["balance"]

        # 获取用户填写的校准说明。
        note = serializer.validated_data.get(
            "note",
            "",
        )

        # 调用账户 Service
        # 执行真正的余额校准。
        account = AccountService.adjust_balance(
            user=request.user,
            account_id=account_id,
            new_balance=new_balance,
            note=note,
        )

        # 将修改后的账户转换为返回数据。
        result = AccountSerializer(account)

        # 返回统一响应。
        return ApiResponse.success(
            message="账户余额校准成功",
            data=result.data,
        )


class AccountBalanceAdjustmentListView(APIView):
    """
    账户余额校准历史接口。

    请求方式：
        GET

    请求地址：
        /api/v1/accounts/{id}/balance-adjustments/
    """

    def get(
        self,
        request,
        account_id,
    ):
        """
        获取指定账户的余额校准历史。
        """

        # 调用 Service 查询历史记录。
        adjustments = AccountService.get_balance_adjustments(
            user=request.user,
            account_id=account_id,
        )

        # 将 QuerySet 转换为返回数据。
        serializer = AccountBalanceAdjustmentSerializer(
            adjustments,
            many=True,
        )

        # 返回统一响应。
        return ApiResponse.success(
            message="获取余额校准记录成功",
            data=serializer.data,
        )


class TransferListCreateView(APIView):
    """
    账户转账记录列表 / 新增接口。

    GET:
        查询当前用户的转账记录。

    POST:
        创建账户内部转账记录。

    请求地址：
        /api/v1/accounts/transfers/
    """

    def get(
        self,
        request,
    ):
        """
        获取当前用户转账记录列表。
        """

        # 调用业务层查询当前用户转账记录。
        transfers = AccountService.get_transfer_list(
            user=request.user,
        )

        # 序列化转账记录。
        serializer = TransferSerializer(
            transfers,
            many=True,
        )

        # 返回统一响应。
        return ApiResponse.success(
            message="获取转账记录成功",
            data=serializer.data,
        )

    def post(
        self,
        request,
    ):
        """
        创建账户内部转账记录。
        """

        # 校验请求参数。
        serializer = TransferCreateSerializer(data=request.data)

        # 执行参数校验。
        serializer.is_valid(raise_exception=True)

        # 调用 Service 创建转账记录。
        transfer = AccountService.create_transfer(
            user=request.user,
            validated_data=(serializer.validated_data),
        )

        # 序列化返回结果。
        result = TransferSerializer(transfer)

        # 返回统一响应。
        return ApiResponse.success(
            message="转账记录创建成功",
            data=result.data,
        )


class TransferDetailView(APIView):
    """
    转账记录详情 / 撤销接口。

    GET:
        获取转账详情。

    DELETE:
        撤销转账。

    请求地址：
        /api/v1/accounts/transfers/{id}/
    """

    def get(
        self,
        request,
        transfer_id,
    ):
        """
        获取指定转账记录详情。
        """

        # 获取当前用户自己的转账记录。
        transfer = AccountService.get_transfer_detail(
            user=request.user,
            transfer_id=transfer_id,
        )

        # 序列化。
        serializer = TransferSerializer(transfer)

        # 返回结果。
        return ApiResponse.success(
            message="获取转账记录详情成功",
            data=serializer.data,
        )

    def delete(
        self,
        request,
        transfer_id,
    ):
        """
        撤销指定转账记录。
        """

        # 调用 Service 执行转账撤销。
        AccountService.delete_transfer(
            user=request.user,
            transfer_id=transfer_id,
        )

        # 返回统一响应。
        return ApiResponse.success(
            message="转账记录撤销成功",
            data=None,
        )
